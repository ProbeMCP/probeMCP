"""Local hardware-lab orchestration primitives."""

from probemcp.lab.interfaces import PowerController, SerialCapture
from probemcp.lab.inventory import LabTarget, TargetInventory, TargetLock

__all__ = ["LabTarget", "PowerController", "SerialCapture", "TargetInventory", "TargetLock"]
