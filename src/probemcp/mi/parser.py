"""Small GDB/MI record parser.

The parser handles the v0.1 subset needed by the controller foundation:
tokenized result records, basic async records, stream records, and the prompt.
It does not execute GDB or interpret target semantics.
"""

from __future__ import annotations

from probemcp.mi.errors import MIParseError
from probemcp.mi.records import MIRecord, MIRecordKind, MIStreamRecord, MIValue


def parse_mi_record(line: str) -> MIRecord | MIStreamRecord:
    """Parse one GDB/MI output line."""

    parser = _MIParser(line.rstrip("\r\n"))
    return parser.parse()


class _MIParser:
    def __init__(self, line: str) -> None:
        self.line = line
        self.position = 0

    def parse(self) -> MIRecord | MIStreamRecord:
        if self.line == "(gdb)":
            return MIRecord(
                kind=MIRecordKind.PROMPT,
                token=None,
                record_class="prompt",
                results={},
                raw=self.line,
            )

        token = self._parse_token()
        marker = self._consume_marker()

        if marker == "^":
            return self._parse_result_or_async(MIRecordKind.RESULT, token)
        if marker == "*":
            return self._parse_result_or_async(MIRecordKind.EXEC_ASYNC, token)
        if marker == "+":
            return self._parse_result_or_async(MIRecordKind.STATUS_ASYNC, token)
        if marker == "=":
            return self._parse_result_or_async(MIRecordKind.NOTIFY_ASYNC, token)
        if marker == "~":
            return self._parse_stream(MIRecordKind.CONSOLE_STREAM, token)
        if marker == "@":
            return self._parse_stream(MIRecordKind.TARGET_STREAM, token)
        if marker == "&":
            return self._parse_stream(MIRecordKind.LOG_STREAM, token)

        raise self._error(f"unsupported record marker {marker!r}")

    def _parse_token(self) -> int | None:
        start = self.position
        while self._peek().isdigit():
            self.position += 1

        if self.position == start:
            return None
        return int(self.line[start : self.position])

    def _consume_marker(self) -> str:
        marker = self._peek()
        if marker == "":
            raise self._error("missing record marker")
        self.position += 1
        return marker

    def _parse_result_or_async(self, kind: MIRecordKind, token: int | None) -> MIRecord:
        record_class = self._parse_identifier(allow_hyphen=True)
        results: dict[str, MIValue] = {}

        if self._peek() == ",":
            self.position += 1
            results = self._parse_result_list(stop_chars="")

        if not self._at_end():
            raise self._error("unexpected trailing data")

        return MIRecord(
            kind=kind,
            token=token,
            record_class=record_class,
            results=results,
            raw=self.line,
        )

    def _parse_stream(self, kind: MIRecordKind, token: int | None) -> MIStreamRecord:
        text = self._parse_c_string()
        if not self._at_end():
            raise self._error("unexpected trailing stream data")
        return MIStreamRecord(kind=kind, token=token, text=text, raw=self.line)

    def _parse_result_list(self, stop_chars: str) -> dict[str, MIValue]:
        results: dict[str, MIValue] = {}
        while not self._at_end() and self._peek() not in stop_chars:
            key, value = self._parse_result()
            results[key] = value
            if self._peek() == ",":
                self.position += 1
                continue
            break
        return results

    def _parse_result(self) -> tuple[str, MIValue]:
        key = self._parse_identifier(allow_hyphen=True)
        self._expect("=")
        return key, self._parse_value()

    def _parse_value(self) -> MIValue:
        current = self._peek()
        if current == '"':
            return self._parse_c_string()
        if current == "{":
            return self._parse_tuple()
        if current == "[":
            return self._parse_list()
        return self._parse_bare_value()

    def _parse_tuple(self) -> dict[str, MIValue]:
        self._expect("{")
        if self._peek() == "}":
            self.position += 1
            return {}
        values = self._parse_result_list(stop_chars="}")
        self._expect("}")
        return values

    def _parse_list(self) -> list[MIValue]:
        self._expect("[")
        values: list[MIValue] = []

        while not self._at_end() and self._peek() != "]":
            if self._next_value_is_result():
                key, value = self._parse_result()
                values.append({key: value})
            else:
                values.append(self._parse_value())

            if self._peek() == ",":
                self.position += 1
                continue
            break

        self._expect("]")
        return values

    def _next_value_is_result(self) -> bool:
        cursor = self.position
        if not self._is_identifier_start(self._peek_at(cursor)):
            return False
        cursor += 1
        while self._is_identifier_part(self._peek_at(cursor), allow_hyphen=True):
            cursor += 1
        return self._peek_at(cursor) == "="

    def _parse_identifier(self, *, allow_hyphen: bool) -> str:
        start = self.position
        if not self._is_identifier_start(self._peek()):
            raise self._error("expected identifier")

        self.position += 1
        while self._is_identifier_part(self._peek(), allow_hyphen=allow_hyphen):
            self.position += 1

        return self.line[start : self.position]

    def _parse_c_string(self) -> str:
        self._expect('"')
        output: list[str] = []

        while not self._at_end():
            current = self._peek()
            self.position += 1

            if current == '"':
                return "".join(output)
            if current == "\\":
                output.append(self._parse_escape())
            else:
                output.append(current)

        raise self._error("unterminated string")

    def _parse_escape(self) -> str:
        if self._at_end():
            raise self._error("unterminated escape")

        escaped = self._peek()
        self.position += 1
        match escaped:
            case "n":
                return "\n"
            case "r":
                return "\r"
            case "t":
                return "\t"
            case "\\":
                return "\\"
            case '"':
                return '"'
            case _:
                return escaped

    def _parse_bare_value(self) -> str:
        start = self.position
        while not self._at_end() and self._peek() not in ",]}":
            self.position += 1

        if self.position == start:
            raise self._error("expected value")
        return self.line[start : self.position]

    def _expect(self, expected: str) -> None:
        if self._peek() != expected:
            raise self._error(f"expected {expected!r}")
        self.position += 1

    def _peek(self) -> str:
        return self._peek_at(self.position)

    def _peek_at(self, position: int) -> str:
        if position >= len(self.line):
            return ""
        return self.line[position]

    def _at_end(self) -> bool:
        return self.position >= len(self.line)

    def _error(self, message: str) -> MIParseError:
        return MIParseError(message, self.line, self.position)

    @staticmethod
    def _is_identifier_start(value: str) -> bool:
        return value.isalpha() or value == "_"

    @staticmethod
    def _is_identifier_part(value: str, *, allow_hyphen: bool) -> bool:
        return value.isalnum() or value == "_" or (allow_hyphen and value == "-")
