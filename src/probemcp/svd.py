"""Minimal CMSIS-SVD loading and peripheral decoding."""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import parse as safe_xml_parse
from pydantic import Field

from probemcp.mcp_server.schemas import SchemaModel


class SVDField(SchemaModel):
    """One peripheral register bitfield."""

    name: str
    bit_offset: int = Field(ge=0)
    bit_width: int = Field(ge=1)
    description: str | None = None

    def decode(self, value: int) -> int:
        """Decode this field from a register value."""

        mask = (1 << self.bit_width) - 1
        return (value >> self.bit_offset) & mask


class SVDRegister(SchemaModel):
    """One peripheral register."""

    name: str
    address_offset: int = Field(ge=0)
    description: str | None = None
    fields: dict[str, SVDField] = Field(default_factory=dict)

    def decode(self, value: int) -> dict[str, int]:
        """Decode all known fields from a register value."""

        return {name: field.decode(value) for name, field in self.fields.items()}


class SVDPeripheral(SchemaModel):
    """One SVD peripheral."""

    name: str
    base_address: int = Field(ge=0)
    description: str | None = None
    registers: dict[str, SVDRegister] = Field(default_factory=dict)

    def register_address(self, register_name: str) -> int:
        """Return the absolute address for a register."""

        return self.base_address + self.registers[register_name].address_offset


class SVDDevice(SchemaModel):
    """Loaded SVD device model."""

    name: str
    peripherals: dict[str, SVDPeripheral] = Field(default_factory=dict)

    def peripheral(self, name: str) -> SVDPeripheral:
        """Return a peripheral by name."""

        return self.peripherals[name]


def load_svd(path: Path) -> SVDDevice:
    """Load a small CMSIS-SVD subset from a local XML file."""

    root = safe_xml_parse(path).getroot()
    if root is None:
        raise ValueError("empty SVD document")
    device_name = _text(root, "name") or path.stem
    peripherals: dict[str, SVDPeripheral] = {}
    for peripheral_node in root.findall("./peripherals/peripheral"):
        peripheral = _parse_peripheral(peripheral_node)
        peripherals[peripheral.name] = peripheral
    return SVDDevice(name=device_name, peripherals=peripherals)


def _parse_peripheral(node: Element[str]) -> SVDPeripheral:
    name = _required_text(node, "name")
    base_address = _parse_int(_required_text(node, "baseAddress"))
    registers: dict[str, SVDRegister] = {}
    for register_node in node.findall("./registers/register"):
        register = _parse_register(register_node)
        registers[register.name] = register
    return SVDPeripheral(
        name=name,
        base_address=base_address,
        description=_text(node, "description"),
        registers=registers,
    )


def _parse_register(node: Element[str]) -> SVDRegister:
    name = _required_text(node, "name")
    fields: dict[str, SVDField] = {}
    for field_node in node.findall("./fields/field"):
        field = SVDField(
            name=_required_text(field_node, "name"),
            bit_offset=_parse_int(_required_text(field_node, "bitOffset")),
            bit_width=_parse_int(_required_text(field_node, "bitWidth")),
            description=_text(field_node, "description"),
        )
        fields[field.name] = field
    return SVDRegister(
        name=name,
        address_offset=_parse_int(_required_text(node, "addressOffset")),
        description=_text(node, "description"),
        fields=fields,
    )


def _required_text(node: Element[str], name: str) -> str:
    value = _text(node, name)
    if value is None:
        raise ValueError(f"missing SVD element: {name}")
    return value


def _text(node: Element[str], name: str) -> str | None:
    child = node.find(name)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _parse_int(value: str) -> int:
    return int(value, 0)
