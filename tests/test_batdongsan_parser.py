import pytest

from collectors.batdongsan_parser import (
    parse_area,
    parse_date,
    parse_list_page,
    parse_price,
)


@pytest.mark.parametrize("text, expected", [
    ("1,8 triệu/tháng", 1_800_000),
    ("4,7 triệu/tháng", 4_700_000),
    ("25 triệu/tháng", 25_000_000),
    ("2,6 tỷ", 2_600_000_000),
    ("23.5 tỷ", 23_500_000_000),
    ("Thỏa thuận", None),
    ("Giá thỏa thuận", None),
    ("1.2.3 triệu", None),
    ("", None),
    (None, None),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("25 m²", 25.0),
    ("12,5 m²", 12.5),
    ("30 m2", 30.0),
    ("", None),
    (None, None),
    ("rộng", None),
])
def test_parse_area(text, expected):
    assert parse_area(text) == expected


@pytest.mark.parametrize("label, expected", [
    ("20/11/2026", "2026-11-20"),
    ("5/1/2026", "2026-01-05"),
    ("2026-11-20", None),
    ("", None),
    (None, None),
])
def test_parse_date(label, expected):
    assert parse_date(label) == expected


# Trang mẫu tự viết, mô phỏng cấu trúc thật (nội dung bịa, không phải dữ liệu của site).
SAMPLE_PAGE = """
<html><body>
<div class="js__card js__card-full-web re__card-full" uid="999" prid="1001">
  <a class="js__product-link-for-product-id" href="/cho-thue-phong-tro/phong-a-pr1001"></a>
  <h3 class="re__card-title"><span class="pr-title js__card-title">  Phòng A   gần trường </span></h3>
  <div class="re__card-config">
    <span class="re__card-config-price">2,5 triệu/tháng</span>
    <span class="re__card-config-dot">·</span>
    <span class="re__card-config-area">20 m²</span>
  </div>
  <div class="re__card-location"><span class="re__card-config-dot">·</span><span>Hà Nội</span></div>
  <div class="re__card-published-info">
    <div class="re__card-published-info-published-at">
      <span class="re__card-published-info-published-at" aria-label="20/11/2026">Đăng hôm nay</span>
    </div>
  </div>
</div>
<div class="js__card js__card-full-web re__card-full" uid="998" prid="1002">
  <h3 class="re__card-title"><span class="js__card-title">Phòng B</span></h3>
  <div class="re__card-config"><span class="re__card-config-price">Thỏa thuận</span></div>
  <div class="re__card-location"><span>Hồ Chí Minh</span></div>
  <span class="re__card-published-info-published-at" aria-label="19/11/2026">Đăng hôm qua</span>
</div>
<div class="js__card js__card-compact-web" prid="2001">
  <h3 class="re__card-title"><span class="js__card-title">Tin gợi ý, phải bị bỏ qua</span></h3>
</div>
</body></html>
"""


def test_list_page_only_main_cards():
    ids = [r["listing_id"] for r in parse_list_page(SAMPLE_PAGE)]
    assert ids == ["1001", "1002"]


def test_card_fields():
    a = parse_list_page(SAMPLE_PAGE)[0]
    assert a["title"] == "Phòng A gần trường"
    assert a["price_vnd"] == 2_500_000
    assert a["area_m2"] == 20.0
    assert a["province_raw"] == "Hà Nội"
    assert a["posted_date"] == "2026-11-20"
    assert a["url_path"] == "/cho-thue-phong-tro/phong-a-pr1001"


def test_negotiable_price_is_none_not_zero():
    b = parse_list_page(SAMPLE_PAGE)[1]
    assert b["price_raw"] == "Thỏa thuận"
    assert b["price_vnd"] is None
    assert b["area_m2"] is None


def test_date_found_in_both_html_shapes():
    # tin 1: ngày nằm trong div bọc ngoài; tin 2: span đứng một mình
    dates = [r["posted_date"] for r in parse_list_page(SAMPLE_PAGE)]
    assert dates == ["2026-11-20", "2026-11-19"]


def test_poster_id_is_never_collected():
    assert "999" not in str(parse_list_page(SAMPLE_PAGE))
    assert "uid" not in str(parse_list_page(SAMPLE_PAGE))