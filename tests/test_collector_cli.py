import json

import pytest

from collectors import collector

PAGE = """
<html><body>
<div class="js__card js__card-full-web" uid="999" prid="1001">
  <h3 class="re__card-title"><span class="js__card-title">Phòng A</span></h3>
  <div class="re__card-config"><span class="re__card-config-price">2,5 triệu/tháng</span>
    <span class="re__card-config-area">20 m²</span></div>
  <div class="re__card-location"><span>Hà Nội</span></div>
  <span class="re__card-published-info-published-at" aria-label="20/11/2026">Đăng hôm nay</span>
</div>
</body></html>
"""


@pytest.fixture
def stored(monkeypatch):
    """Thay phần ghi vào RustFS bằng một danh sách ghi nhớ, không cần RustFS chạy."""
    saved = []
    monkeypatch.setattr(collector, "get_client", lambda: object())
    monkeypatch.setattr(collector, "get_bucket", lambda: "test-bucket")
    monkeypatch.setattr(collector, "ensure_bucket", lambda client, bucket: None)

    def fake_put(client, bucket, key, payload):
        saved.append((bucket, key, payload))
        return len(json.dumps(payload))

    monkeypatch.setattr(collector, "put_json", fake_put)
    return saved


def test_parser_knows_the_html_file_options():
    args = collector.build_parser().parse_args(
        ["--source", "batdongsan", "--html-file", "a.html", "--snapshot-date", "2026-11-20"]
    )
    assert args.source == "batdongsan"
    assert args.html_file == "a.html"
    assert args.snapshot_date == "2026-11-20"


def test_default_source_is_mock():
    assert collector.build_parser().parse_args([]).source == "mock"


def test_html_file_flows_into_bronze_under_batdongsan_prefix(tmp_path, stored):
    page = tmp_path / "page.html"
    page.write_text(PAGE, encoding="utf-8")
    collector.main(["--source", "batdongsan", "--html-file", str(page), "--snapshot-date", "2026-11-18"])
    (bucket, key, payload), = stored
    assert key.startswith("source=batdongsan/dt=2026-11-18/batch_id=")
    assert payload["method"] == "manual_save"
    assert payload["record_count"] == 1


def test_mock_still_works_from_the_command_line(stored):
    collector.main(["--day", "2"])
    (bucket, key, payload), = stored
    assert key.startswith("source=mock/dt=2026-11-02/")


def test_missing_html_file_exits_with_code_1(stored):
    with pytest.raises(SystemExit) as exc:
        collector.main(["--source", "batdongsan", "--html-file", "khong_ton_tai.html"])
    assert exc.value.code == 1
    assert stored == []


def test_bad_snapshot_date_exits_with_code_1(tmp_path, stored):
    page = tmp_path / "p.html"
    page.write_text(PAGE, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        collector.main(["--source", "batdongsan", "--html-file", str(page), "--snapshot-date", "20-11-2026"])
    assert exc.value.code == 1
    assert stored == []