"""Tách tin đăng từ trang danh sách Nhà Tốt.

Trang là ứng dụng Next.js: toàn bộ dữ liệu của các tin nằm sẵn trong một khối JSON
(`__NEXT_DATA__`). Đọc khối này ổn định hơn dò từng thẻ HTML khi giao diện đổi.
"""
import json
from datetime import datetime, timezone

from bs4 import BeautifulSoup


def _ads(soup):
    """Lấy danh sách tin trong __NEXT_DATA__. Thiếu khối hoặc JSON hỏng thì trả []."""
    script = soup.find("script", id="__NEXT_DATA__")
    if script is None:
        return []
    try:
        data = json.loads(script.string or "")
        ads = data["props"]["initialState"]["adlisting"]["data"]["ads"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []
    return ads if isinstance(ads, list) else []


def _number(value):
    """Chỉ nhận số thật; giá trị lạ thì None (không đoán)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _epoch_ms_to_iso(value):
    """Mốc thời gian dạng mili-giây -> chuỗi ISO UTC. Không có thì None."""
    ms = _number(value)
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def parse_ad(ad, position):
    """Một tin -> dict. Cố ý KHÔNG đọc hồ sơ người đăng (account_*, full_name, avatar,
    seller_info), số điện thoại, mô tả (body) và ảnh."""
    list_id = ad.get("list_id")
    return {
        "listing_id": str(list_id) if list_id is not None else None,
        "position": position,
        "title": ad.get("subject"),
        "price_vnd": _number(ad.get("price")),
        "original_price_vnd": _number(ad.get("original_price")),
        "area_m2": _number(ad.get("size")),
        "property_type": ad.get("category_name"),
        "province_raw": ad.get("region_name"),
        "district_raw": ad.get("area_name"),
        "ward_raw": ad.get("ward_name"),
        "street_raw": ad.get("street_name"),
        "latitude": _number(ad.get("latitude")),
        "longitude": _number(ad.get("longitude")),
        "deposit_vnd": _number(ad.get("deposit")),
        "posted_at": _epoch_ms_to_iso(ad.get("orig_list_time")),
        "status": ad.get("status"),
    }


def parse_list_page(html):
    """Trang danh sách -> list dict, đúng thứ tự trên trang."""
    soup = BeautifulSoup(html, "html.parser")
    return [parse_ad(ad, i) for i, ad in enumerate(_ads(soup), start=1) if isinstance(ad, dict)]