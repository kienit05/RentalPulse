import pytest

from etl import purge_batch


class FakeClient:
    """Giả lập client S3 vừa đủ cho find_bronze_keys."""

    def __init__(self, keys):
        self.keys = keys

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        keys = self.keys

        class Paginator:
            def paginate(self, Bucket):
                yield {"Contents": [{"Key": k} for k in keys]}

        return Paginator()


KEYS = [
    "source=nhatot/dt=2026-11-21/batch_id=20261120T172318Z-28a9d0/listings.json",
    "source=nhatot/dt=2026-11-20/batch_id=20261120T145506Z-20f522/listings.json",
    "source=mock/dt=2026-11-01/batch_id=20261120T170158Z-e59067/listings.json",
]


def test_only_the_requested_batch_is_found():
    found = purge_batch.find_bronze_keys(FakeClient(KEYS), "b", "20261120T172318Z-28a9d0")
    assert found == [KEYS[0]]


def test_unknown_batch_finds_nothing():
    assert purge_batch.find_bronze_keys(FakeClient(KEYS), "b", "20991231T235959Z-ffffff") == []


@pytest.mark.parametrize("bad", ["", "nhatot", "20261120T172318Z", "../../x", "20261120T172318Z-28a9d0/", "20261120T172318Z-XYZ123"])
def test_malformed_batch_id_is_rejected_before_touching_anything(bad):
    with pytest.raises(SystemExit) as exc:
        purge_batch.main([bad, "--yes"])
    assert exc.value.code == 1