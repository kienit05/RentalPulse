"""Test lọc batch mới cho publish_batch --only-new."""
import pytest

from etl.publish_batch import batch_id_from_key, filter_new_keys

KEY_A = "source=nhatot/dt=2026-11-21/batch_id=20261121T030000Z-aaaaaa/listings.json"
KEY_B = "source=mock/dt=2026-11-02/batch_id=20261120T170207Z-bbbbbb/listings.json"


def test_batch_id_from_key():
    assert batch_id_from_key(KEY_A) == "20261121T030000Z-aaaaaa"


@pytest.mark.parametrize("key", ["", "source=x/listings.json", "batch_id=/listings.json"])
def test_batch_id_from_key_missing_returns_none(key):
    assert batch_id_from_key(key) is None


def test_filter_new_keys_drops_loaded_batches():
    assert filter_new_keys([KEY_A, KEY_B], {"20261121T030000Z-aaaaaa"}) == [KEY_B]


def test_filter_new_keys_keeps_all_when_nothing_loaded():
    assert filter_new_keys([KEY_A, KEY_B], set()) == [KEY_A, KEY_B]


def test_filter_new_keys_keeps_key_without_batch_id():
    odd = "source=x/listings.json"
    assert filter_new_keys([odd], {"abc"}) == [odd]