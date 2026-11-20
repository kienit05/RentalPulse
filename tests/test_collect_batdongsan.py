import re

import pytest

from collectors.collector import collect_batdongsan

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


class FakeFetcher:
    def __init__(self, html):
        self.html = html
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        return self.html


def test_batch_has_source_metadata_and_stamped_records():
    batch = collect_batdongsan("https://example.test/list", FakeFetcher(PAGE))
    assert batch["source"] == "batdongsan"
    assert batch["url"] == "https://example.test/list"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", batch["snapshot_date"])
    assert batch["record_count"] == len(batch["records"]) == 1
    record = batch["records"][0]
    assert record["source"] == "batdongsan"
    assert record["snapshot_date"] == batch["snapshot_date"]
    assert record["listing_id"] == "1001"


def test_page_with_no_listings_is_an_error_not_an_empty_batch():
    with pytest.raises(ValueError):
        collect_batdongsan("https://example.test/list", FakeFetcher("<html></html>"))


def test_poster_id_does_not_reach_bronze():
    batch = collect_batdongsan("https://example.test/list", FakeFetcher(PAGE))
    assert "999" not in str(batch)