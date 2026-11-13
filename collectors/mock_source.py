"""Nguồn dữ liệu giả lập: tạo tin đăng thuê nhà trông giống thật, có cả dữ liệu bẩn."""
import random
from datetime import datetime, timedelta

# Quận -> danh sách đường (dữ liệu mẫu để ghép thành địa chỉ)
DISTRICTS = {
    "Cầu Giấy": ["Trần Thái Tông", "Dịch Vọng Hậu", "Nguyễn Khang"],
    "Hà Đông": ["Nguyễn Trác", "Quang Trung", "Văn Quán"],
    "Thanh Xuân": ["Nguyễn Trãi", "Khuất Duy Tiến", "Lê Văn Lương"],
    "Đống Đa": ["Tây Sơn", "Chùa Bộc", "Láng Hạ"],
    "Nam Từ Liêm": ["Mỹ Đình", "Hồ Tùng Mậu", "Trần Hữu Dực"],
}

# Loại hình -> (diện tích nhỏ nhất, lớn nhất, giá/m2 thấp nhất, cao nhất) tính bằng VND
PROPERTY_TYPES = {
    "Phòng trọ": (15, 35, 120_000, 200_000),
    "Chung cư mini": (25, 50, 150_000, 250_000),
    "Căn hộ": (40, 90, 200_000, 350_000),
    "Nhà nguyên căn": (50, 120, 150_000, 250_000),
}


def format_price(price_vnd, rng):
    """Viết giá theo nhiều kiểu khác nhau, giống người đăng tin thật."""
    millions = price_vnd / 1_000_000
    styles = [
        f"{millions:.1f} triệu/tháng",                 # 3.5 triệu/tháng
        f"{millions:.1f}".replace(".", ",") + " triệu",  # 3,5 triệu
        f"{millions:.1f}tr",                            # 3.5tr
        str(price_vnd),                                 # 3500000
        f"{price_vnd:,}".replace(",", ".") + "đ",       # 3.500.000đ
        "Thỏa thuận",                                   # không có giá
    ]
    return rng.choices(styles, weights=[30, 20, 15, 15, 15, 5])[0]


def format_area(area, rng):
    """Diện tích cũng viết nhiều kiểu, đôi khi bị thiếu."""
    styles = [f"{area}m2", f"{area} m²", str(area), None]
    return rng.choices(styles, weights=[40, 30, 25, 5])[0]


def make_listing(rng, listing_id, now):
    """Tạo MỘT tin đăng."""
    ptype = rng.choice(list(PROPERTY_TYPES))
    a_min, a_max, p_min, p_max = PROPERTY_TYPES[ptype]
    area = rng.randint(a_min, a_max)
    price = int(round(area * rng.randint(p_min, p_max), -5))  # làm tròn đến trăm nghìn
    district = rng.choice(list(DISTRICTS))
    street = rng.choice(DISTRICTS[district])
    posted_at = now - timedelta(days=rng.randint(0, 29), minutes=rng.randint(0, 1439))

    return {
        "listing_id": listing_id,
        "title": f"{ptype} {area}m2 {street} giá tốt",
        "property_type": ptype,
        "price_raw": format_price(price, rng),
        "area_raw": format_area(area, rng),
        "district_raw": rng.choices(
            [district, f"Q. {district}", district.upper()], weights=[70, 15, 15]
        )[0],
        "address_raw": f"Số {rng.randint(1, 200)}, {street}, {district}",
        "posted_at": posted_at.isoformat(),
        "source": "mock",
    }


def generate_batch(n, seed=42, duplicate_rate=0.1, start_id=1, now=None):
    """Tạo n tin đăng, cộng thêm một ít tin đăng lại (trùng nội dung, khác mã)."""
    rng = random.Random(seed)  # seed cố định -> chạy lại cho kết quả giống nhau
    now = now or datetime.now()

    listings = [make_listing(rng, f"RP-{start_id + i:06d}", now) for i in range(n)]

    reposts = []
    next_id = start_id + n
    for item in listings:
        if rng.random() < duplicate_rate:
            dup = dict(item)  # sao chép nguyên nội dung
            dup["listing_id"] = f"RP-{next_id:06d}"  # nhưng mã tin khác
            dup["title"] = item["title"] + " (đăng lại)"
            reposts.append(dup)
            next_id += 1

    batch = listings + reposts
    rng.shuffle(batch)
    return batch


if __name__ == "__main__":
    import json

    data = generate_batch(20)
    print(f"Tạo {len(data)} tin đăng. 3 tin đầu:")
    for item in data[:3]:
        print(json.dumps(item, ensure_ascii=False, indent=2))