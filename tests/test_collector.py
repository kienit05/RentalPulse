import re

from collectors.collector import bronze_key, collect, new_batch_id
from collectors.mock_source import snapshot


def test_bronze_key_follows_convention():
    key = bronze_key("mock", "2026-11-03", "20261118T105204Z-0b4867")
    assert key == "source=mock/dt=2026-11-03/batch_id=20261118T105204Z-0b4867/listings.json"


def test_batch_id_has_expected_format():
    assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{6}", new_batch_id())


def test_two_consecutive_batch_ids_differ():
    assert new_batch_id() != new_batch_id()


def test_collect_packages_a_snapshot_into_a_batch():
    batch = collect(day=3, seed=42)
    assert batch["source"] == "mock"
    assert batch["snapshot_date"] == "2026-11-03"
    assert batch["record_count"] == len(batch["records"]) == len(snapshot(3, seed=42))
    assert batch["record_count"] > 0