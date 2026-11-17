"""Nguồn dữ liệu giả lập: tạo tin đăng thuê nhà trông giống thật, có cả dữ liệu bẩn."""
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

P_NO_PRICE = 0.05 

NEW_PER_DAY = (2, 6)  # mỗi ngày (từ ngày 2) có từ 2 đến 6 tin mới

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

@dataclass
class Listing:
    """Trạng thái THẬT của một tin đăng."""
    listing_id: str
    ptype: str
    area: int
    price: int | None   # None nghĩa là "Thỏa thuận"
    district: str
    street: str
    house_no: int
    created_day: int     # ngày (1, 2, 3...) tin xuất hiện lần đầu
    active: bool = True  # True = website đang hiển thị tin này

def random_listing(rng, listing_id, created_day):
    """Tạo MỘT tin đăng ngẫu nhiên, dưới dạng trạng thái THẬT (sạch)."""
    ptype = rng.choice(list(PROPERTY_TYPES))
    a_min, a_max, p_min, p_max = PROPERTY_TYPES[ptype]
    area = rng.randint(a_min, a_max)
    price = int(round(area * rng.randint(p_min, p_max), -5))  # làm tròn trăm nghìn
    if rng.random() < P_NO_PRICE:
        price = None
    district = rng.choice(list(DISTRICTS))
    street = rng.choice(DISTRICTS[district])
    return Listing(
        listing_id=listing_id,
        ptype=ptype,
        area=area,
        price=price,
        district=district,
        street=street,
        house_no=rng.randint(1, 200),
        created_day=created_day,
    )

# Kịch bản cố định: "số phận" của từng tin theo ngày.
# events có dạng {ngày: [(hành động, giá trị), ...]}
SCENARIOS = [
    {
        "id": "RP-S001",
        "note": "Tin A: giá tăng, biến mất, xuất hiện lại",
        "base": dict(ptype="Phòng trọ", area=25, price=3_500_000,
                     district="Cầu Giấy", street="Trần Thái Tông", house_no=12),
        "events": {
            2: [("set_price", 4_000_000)],
            3: [("remove", None)],
            4: [("return", None)],
        },
    },
]


def apply_scenarios(listings, day):
    """Đưa các tin kịch bản về đúng trạng thái của ngày `day`.

    listings là từ điển {listing_id: Listing}, được cập nhật tại chỗ.
    """
    for sc in SCENARIOS:
        sid = sc["id"]
        if day == sc.get("start_day", 1):
            listings[sid] = Listing(listing_id=sid, created_day=day, **sc["base"])
        listing = listings.get(sid)
        if listing is None:
            continue
        for action, value in sc["events"].get(day, []):
            if action == "set_price":
                listing.price = value
            elif action == "remove":
                listing.active = False
            elif action == "return":
                listing.active = True

def simulate(day, seed=42, n_initial=30):
    """Chạy mô phỏng từ ngày 1 đến ngày `day`.

    Trả về danh sách Listing (cả tin đang hiển thị lẫn tin đã bị gỡ).
    """
    rng = random.Random(seed)
    listings = {}   # {listing_id: Listing}
    counter = 0

    for d in range(1, day + 1):
        apply_scenarios(listings, d)

        n_new = n_initial if d == 1 else rng.randint(*NEW_PER_DAY)
        for _ in range(n_new):
            counter += 1
            listing = random_listing(rng, f"RP-{counter:06d}", created_day=d)
            listings[listing.listing_id] = listing

    return list(listings.values())

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