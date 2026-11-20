import json

import pytest

from collectors.nhatot_parser import parse_list_page


def make_page(ads):
    data = {"props": {"initialState": {"adlisting": {"data": {"ads": ads}}}}}
    return (
        "<html><body><script id=\"__NEXT_DATA__\" type=\"application/json\">"
        + json.dumps(data, ensure_ascii=False)
        + "</script></body></html>"
    )


AD_NORMAL = {
    "list_id": 135951046,
    "subject": "Phòng trọ gần trường",
    "price": 3600000,
    "original_price": 3600000,
    "size": 25,
    "category_name": "Phòng trọ",
    "region_name": "Hà Nội",
    "area_name": "Quận Bắc Từ Liêm",
    "ward_name": "Phường Xuân Đỉnh",
    "street_name": "Nguyễn Đạo An",
    "latitude": 21.07,
    "longitude": 105.78,
    "deposit": 3600000,
    "orig_list_time": 1794795443000,
    "status": "active",
    # các trường về người đăng: không được đi vào kết quả
    "account_id": 777,
    "account_name": "NGUOI_DANG_GIA",
    "full_name": "NGUOI_DANG_GIA",
    "phone": "0900000000",
    "body": "Gọi 0911111111",
    "seller_info": {"name": "NGUOI_DANG_GIA"},
}
AD_PRICE_DROP = {**AD_NORMAL, "list_id": 131123218, "price": 3200000, "original_price": 3500000}
AD_NO_TIME = {**AD_NORMAL, "list_id": 135667716, "orig_list_time": None}


def test_parses_listings_in_page_order():
    records = parse_list_page(make_page([AD_NORMAL, AD_PRICE_DROP, AD_NO_TIME]))
    assert [r["listing_id"] for r in records] == ["135951046", "131123218", "135667716"]
    assert [r["position"] for r in records] == [1, 2, 3]


def test_fields_are_mapped():
    r = parse_list_page(make_page([AD_NORMAL]))[0]
    assert r["title"] == "Phòng trọ gần trường"
    assert r["price_vnd"] == 3_600_000
    assert r["area_m2"] == 25
    assert r["province_raw"] == "Hà Nội"
    assert r["district_raw"] == "Quận Bắc Từ Liêm"
    assert r["ward_raw"] == "Phường Xuân Đỉnh"
    assert r["street_raw"] == "Nguyễn Đạo An"
    assert r["latitude"] == pytest.approx(21.07)
    assert r["status"] == "active"


def test_price_drop_keeps_both_prices():
    r = parse_list_page(make_page([AD_PRICE_DROP]))[0]
    assert r["original_price_vnd"] == 3_500_000
    assert r["price_vnd"] == 3_200_000


def test_posted_at_is_iso_utc_from_epoch_ms():
    r = parse_list_page(make_page([AD_NORMAL]))[0]
    assert r["posted_at"] == "2026-11-16T02:17:23+00:00"


def test_missing_posted_time_is_none():
    assert parse_list_page(make_page([AD_NO_TIME]))[0]["posted_at"] is None


def test_poster_profile_and_contact_fields_are_never_collected():
    blob = str(parse_list_page(make_page([AD_NORMAL])))
    assert "NGUOI_DANG_GIA" not in blob
    assert "0900000000" not in blob
    assert "0911111111" not in blob
    assert "account" not in blob


def test_odd_values_become_none_not_guesses():
    ad = {**AD_NORMAL, "price": "3 triệu", "size": None}
    r = parse_list_page(make_page([ad]))[0]
    assert r["price_vnd"] is None
    assert r["area_m2"] is None


@pytest.mark.parametrize("html", [
    "<html></html>",
    "<html><script id=\"__NEXT_DATA__\">{khong phai json</script></html>",
    "<html><script id=\"__NEXT_DATA__\">{\"props\": {}}</script></html>",
])
def test_page_without_usable_data_gives_empty_list(html):
    assert parse_list_page(html) == []