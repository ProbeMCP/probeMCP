from pathlib import Path

from probemcp.mi.parser import parse_mi_record

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mi"


def test_mi_transcript_corpus_parses_all_nonblank_lines() -> None:
    parsed = []
    for transcript in sorted(FIXTURE_DIR.glob("*.mi")):
        for line in transcript.read_text(encoding="utf-8").splitlines():
            if line.strip():
                parsed.append(parse_mi_record(line))

    assert parsed
    assert any(record.raw.startswith("*stopped") for record in parsed)
