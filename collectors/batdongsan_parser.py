"""Tách dữ liệu từ trang danh sách Batdongsan (HTML -> danh sách dict)."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

# Khớp "1,8 triệu/tháng", "25 triệu", "2,6 tỷ", "23.5 tỷ"
_PRICE = re.compile(r"^\s*([\d.,]+)\s*(triệu|tỷ)(?:\s*/\s*tháng)?\s*$", re.IGNORECASE)
_UNIT = {"triệu": 1_000_000, "tỷ": 1_000_000_000}
# Khớp "25 m²", "12,5 m²"
_AREA = re.compile(r"^\s*([\d.,]+)\s*m[²2]\s*$", re.IGNORECASE)
# Khớp "Q. Nam Từ Liêm (P. Đại Mỗ mới)", "H. Đông Anh", "TX. Sơn Tây"
_LOCATION = re.compile(r"^((?:Q|H|TX|TP)\.\s*[^()]+?)\s*(?:\((.+)\))?$", re.IGNORECASE)
# Chữ "mới" cuối tên phường: site đánh dấu phường sau sáp nhập 2025
_NEW_SUFFIX = re.compile(r"\s+mới$", re.IGNORECASE)


def _to_decimal(text):
    try:
        return Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None


def parse_price(text):
    """Chuỗi giá của site -> số đồng (int). Không hiểu được thì trả None."""
    if not text:
        return None
    match = _PRICE.match(text)
    if not match:
        return None  # "Thỏa thuận" hoặc dạng lạ: không đoán, trả None
    number = _to_decimal(match.group(1))
    if number is None:
        return None
    return int(number * _UNIT[match.group(2).lower()])


def parse_area(text):
    """Chuỗi diện tích -> số m² (float). Không hiểu được thì trả None."""
    if not text:
        return None
    match = _AREA.match(text)
    if not match:
        return None
    number = _to_decimal(match.group(1))
    return float(number) if number is not None else None


def parse_date(label):
    """'20/11/2026' -> '2026-11-20'. Sai định dạng thì trả None."""
    try:
        return datetime.strptime(label, "%d/%m/%Y").date().isoformat()
    except (TypeError, ValueError):
        return None


def parse_location(text):
    """Dòng địa điểm của thẻ -> (tỉnh, quận, phường), phần không có là None.

    'Q. Nam Từ Liêm (P. Đại Mỗ mới)' -> (None, 'Q. Nam Từ Liêm', 'P. Đại Mỗ')
    'H. Đông Anh'                    -> (None, 'H. Đông Anh', None)
    'Hà Nội' (trang toàn quốc)       -> ('Hà Nội', None, None)
    Giữ tiền tố Q./H./P.: staging.normalize_district đã biết bỏ tiền tố quận.
    """
    if not text:
        return None, None, None
    text = " ".join(text.split())
    match = _LOCATION.match(text)
    if match is None:
        return text, None, None
    district, ward = match.groups()
    if ward:
        ward = _NEW_SUFFIX.sub("", ward.strip()) or None
    return None, district.strip(), ward


def _text(card, css):
    """Văn bản của phần tử đầu tiên khớp css, gọn khoảng trắng; không có thì None."""
    tag = card.select_one(css)
    if tag is None:
        return None
    return " ".join(tag.get_text(" ", strip=True).split()) or None


def parse_card(card):
    """Một thẻ tin -> dict. Cố ý KHÔNG đọc uid (mã người đăng)."""
    price_raw = _text(card, ".re__card-config-price")
    area_raw = _text(card, ".re__card-config-area")
    link = card.select_one("a.js__product-link-for-product-id")
    published = card.select_one("span.re__card-published-info-published-at")
    location = card.select_one(".re__card-location")
    location_text = None
    if location is not None:
        spans = [s.get_text(strip=True) for s in location.find_all("span")]
        spans = [s for s in spans if s and s != "·"]
        location_text = spans[-1] if spans else None
    province, district, ward = parse_location(location_text)
    return {
        "listing_id": card.get("prid"),
        "title": _text(card, ".js__card-title"),
        "price_raw": price_raw,
        "price_vnd": parse_price(price_raw),
        "area_raw": area_raw,
        "area_m2": parse_area(area_raw),
        "province_raw": province,
        "district_raw": district,
        "ward_raw": ward,
        "posted_date": parse_date(published.get("aria-label")) if published else None,
        "url_path": link.get("href") if link else None,
    }


def parse_list_page(html):
    """Trang danh sách -> list dict. Chỉ lấy thẻ danh sách chính (full-web)."""
    soup = BeautifulSoup(html, "html.parser")
    return [parse_card(c) for c in soup.select("div.js__card-full-web")]