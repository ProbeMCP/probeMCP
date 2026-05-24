from datetime import UTC, datetime, timedelta

import pytest

from probemcp.lab.inventory import LabTarget, TargetInventory, TargetLock
from probemcp.mcp_server.schemas import BackendKind
from probemcp.rtos.freertos import FreeRTOSTask, FreeRTOSTaskState, summarize_tasks
from probemcp.safety.policy import TargetClass
from probemcp.svd import SVDField, load_svd


def test_svd_loader_decodes_register_fields(tmp_path) -> None:
    svd_path = tmp_path / "demo.svd"
    svd_path.write_text(
        """
<device>
  <name>Demo</name>
  <peripherals>
    <peripheral>
      <name>GPIOA</name>
      <baseAddress>0x40020000</baseAddress>
      <registers>
        <register>
          <name>MODER</name>
          <addressOffset>0x00</addressOffset>
          <fields>
            <field><name>MODE0</name><bitOffset>0</bitOffset><bitWidth>2</bitWidth></field>
            <field><name>MODE1</name><bitOffset>2</bitOffset><bitWidth>2</bitWidth></field>
          </fields>
        </register>
      </registers>
    </peripheral>
  </peripherals>
</device>
""",
        encoding="utf-8",
    )

    device = load_svd(svd_path)
    gpioa = device.peripheral("GPIOA")
    register = gpioa.registers["MODER"]

    assert gpioa.register_address("MODER") == 0x40020000
    assert register.decode(0b1001) == {"MODE0": 1, "MODE1": 2}


def test_svd_field_decodes_bit_range() -> None:
    assert SVDField(name="ENABLE", bit_offset=4, bit_width=1).decode(0b10000) == 1


def test_freertos_task_summary_flags_current_and_low_stack_tasks() -> None:
    tasks = [
        FreeRTOSTask(
            name="main",
            state=FreeRTOSTaskState.RUNNING,
            priority=3,
            current=True,
            stack_high_water_mark=128,
        ),
        FreeRTOSTask(
            name="worker",
            state=FreeRTOSTaskState.BLOCKED,
            priority=2,
            stack_high_water_mark=8,
        ),
    ]

    summary = summarize_tasks(tasks)

    assert summary["current_task"] == "main"
    assert summary["states"] == {"running": 1, "blocked": 1}
    assert summary["low_stack_tasks"] == ["worker"]


def test_target_inventory_locks_and_releases_targets() -> None:
    inventory = TargetInventory(
        [
            LabTarget(
                target_id="board-1",
                backend=BackendKind.OPENOCD,
                endpoint="localhost:3333",
                target_class=TargetClass.DEVELOPMENT_HARDWARE,
            )
        ]
    )

    lock = inventory.acquire("board-1", owner="test", ttl_seconds=60)

    with pytest.raises(RuntimeError, match="already locked"):
        inventory.acquire("board-1", owner="other", ttl_seconds=60)

    inventory.release(lock.lock_id)
    assert inventory.acquire("board-1", owner="other", ttl_seconds=60).owner == "other"


def test_target_lock_expiry_and_missing_target_errors() -> None:
    lock = TargetLock(
        target_id="board-1",
        owner="test",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    inventory = TargetInventory()

    assert lock.expired()
    assert inventory.list_targets() == []
    with pytest.raises(KeyError, match="target not found"):
        inventory.acquire("missing", owner="test")
    with pytest.raises(KeyError, match="lock not found"):
        inventory.release("missing")
