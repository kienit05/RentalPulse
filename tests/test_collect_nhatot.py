import json

import pytest

from collectors import collector
from collectors.collector import collect_nhatot_html

AD = {"list_id": 1001, "subject": "Phòng A", "price": 3000000, "original_price": 3000000, "size": 20,
      "region_name": "Hà Nội", "area_name": "Quận Cầu Giấy", "status": "active"}
PAGE = (
    "<html><script id=\"__NEXT_DATA__\" type=\"application/json\">"
    + json.dumps({"props": {"initialState": {"adlisting": {"data": {"ads": [AD]}}}}})
    + "</script></html>"
)


def test_batch_has_source_metadata_and_stamped_records():
    batch = collect_nhatot_html(PAGE, "https://example.test/list", "2026-11-20")
    assert batch["source"] == "nhatot"
    assert batch["method"] == "manual_save"
    assert batch["snapshot_date"] == "2026-11-20"
    assert batch["record_count"] == 1
    record = batch["records"][0]
    assert record["source"] == "nhatot"
    assert record["snapshot_date"] == "2026-11-20"
    assert record["listing_id"] == "1001"


def test_page_with_no_listings_is_an_error():
    with pytest.raises(ValueError):
        collect_nhatot_html("<html></html>", "https://example.test/list")


@pytest.fixture
def stored(monkeypatch):
    saved = []
    monkeypatch.setattr(collector, "get_client", lambda: object())
    monkeypatch.setattr(collector, "get_bucket", lambda: "test-bucket")
    monkeypatch.setattr(collector, "ensure_bucket", lambda client, bucket: None)
    monkeypatch.setattr(collector, "put_json", lambda c, b, k, p: saved.append((b, k, p)) or 1)
    return saved


def test_cli_saved_page_lands_under_nhatot_prefix(tmp_path, stored):
    page = tmp_path / "p.html"
    page.write_text(PAGE, encoding="utf-8")
    collector.main(["--source", "nhatot", "--html-file", str(page), "--snapshot-date", "2026-11-18"])
    (bucket, key, payload), = stored
    assert key.startswith("source=nhatot/dt=2026-11-18/batch_id=")
    assert payload["record_count"] == 1


def test_cli_nhatot_refuses_automatic_download(stored):
    with pytest.raises(SystemExit) as exc:
        collector.main(["--source", "nhatot"])
    assert exc.value.code == 1
    assert stored == []


# Một trang Batdongsan hợp lệ: nếu lệnh mock + --html-file lọt qua, trang này sẽ cho ra tin
# và bị lưu. Vì thế test chỉ xanh khi dòng bảo vệ thật sự chạy.
BATDONGSAN_PAGE = """
<html><body>
<div class="js__card js__card-full-web" prid="1001">
  <h3 class="re__card-title"><span class="js__card-title">Phòng A</span></h3>
  <div class="re__card-config"><span class="re__card-config-price">2,5 triệu/tháng</span>
    <span class="re__card-config-area">20 m²</span></div>
  <div class="re__card-location"><span>Hà Nội</span></div>
  <span class="re__card-published-info-published-at" aria-label="20/11/2026">Đăng hôm nay</span>
</div>
</body></html>
"""


def test_cli_mock_rejects_html_file(tmp_path, stored):
    page = tmp_path / "p.html"
    page.write_text(BATDONGSAN_PAGE, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        collector.main(["--source", "mock", "--html-file", str(page)])
    assert exc.value.code == 1
    assert stored == []