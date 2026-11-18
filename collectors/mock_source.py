"""Nguồn dữ liệu giả lập: tạo tin đăng thuê nhà trông giống thật, có cả dữ liệu bẩn."""
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

P_PRICE_CHANGE = 0.06  # xác suất mỗi ngày một tin đang hiển thị đổi giá
P_NO_PRICE = 0.05  # xác suất một tin ghi "Thỏa thuận" (chưa có giá)
NEW_PER_DAY = (2, 6)  # mỗi ngày (từ ngày 2) có từ 2 đến 6 tin mới
P_REMOVE = 0.04   # xác suất mỗi ngày một tin đang hiển thị bị gỡ
P_REPOST = 0.30   # trong số tin bị gỡ, xác suất được đăng lại bằng mã mới
P_RETURN = 0.15   # xác suất mỗi ngày một tin đã gỡ (chưa đăng lại) xuất hiện lại
START_DATE = date(2026, 11, 1)  # ngày 1 của mô phỏng

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
    scripted: bool = False  # True = tin kịch bản, chỉ đổi theo kịch bản
    is_repost: bool = False  # True = bản đăng lại của một tin khác
    reposted: bool = False   # True = tin này đã có bản đăng lại, sẽ không quay lại nữa

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

def new_price(price, rng):
    """Đổi giá ngẫu nhiên khoảng 5% đến 10%, làm tròn đến trăm nghìn."""
    factor = rng.choice([-0.10, -0.05, 0.05, 0.10])
    new = int(round(price * (1 + factor), -5))
    return new if new != price else price + 100_000

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
    {
        "id": "RP-S002",
        "note": "Giá giảm ở ngày 3",
        "base": dict(ptype="Căn hộ", area=60, price=8_000_000,
                     district="Nam Từ Liêm", street="Mỹ Đình", house_no=88),
        "events": {3: [("set_price", 7_500_000)]},
    },
    {
        "id": "RP-S003",
        "note": "Từ 'Thỏa thuận' sang có giá ở ngày 3",
        "base": dict(ptype="Chung cư mini", area=30, price=None,
                     district="Thanh Xuân", street="Nguyễn Trãi", house_no=45),
        "events": {3: [("set_price", 5_000_000)]},
    },
    {
        "id": "RP-S004",
        "note": "Bị gỡ ở ngày 3, được đăng lại bằng mã S005",
        "base": dict(ptype="Phòng trọ", area=20, price=3_000_000,
                     district="Hà Đông", street="Nguyễn Trác", house_no=7),
        "events": {3: [("remove", None)]},
    },
    {
        "id": "RP-S005",
        "note": "Bản đăng lại của S004: cùng căn phòng, mã mới",
        "start_day": 3,
        "is_repost": True,
        "base": dict(ptype="Phòng trọ", area=20, price=3_000_000,
                     district="Hà Đông", street="Nguyễn Trác", house_no=7),
        "events": {},
    },
    {
        "id": "RP-S006",
        "note": "Không bao giờ thay đổi (đối chứng)",
        "base": dict(ptype="Nhà nguyên căn", area=80, price=15_000_000,
                     district="Đống Đa", street="Tây Sơn", house_no=101),
        "events": {},
    },
]


def apply_scenarios(listings, day):
    """Đưa các tin kịch bản về đúng trạng thái của ngày `day`.

    listings là từ điển {listing_id: Listing}, được cập nhật tại chỗ.
    """
    for sc in SCENARIOS:
        sid = sc["id"]
        if day == sc.get("start_day", 1):
                        listings[sid] = Listing(listing_id=sid, created_day=day, scripted=True,
                                    is_repost=sc.get("is_repost", False), **sc["base"])
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

        # 1) Biến động của các tin đã có (từ ngày 2)
        if d > 1:
            for listing in list(listings.values()):
                if listing.scripted:
                    continue
                if listing.active:
                    r = rng.random()
                    if r < P_REMOVE:
                        listing.active = False
                        if rng.random() < P_REPOST:
                            listing.reposted = True
                            counter += 1
                            new_id = f"RP-{counter:06d}"
                            listings[new_id] = Listing(
                                listing_id=new_id, ptype=listing.ptype, area=listing.area,
                                price=listing.price, district=listing.district,
                                street=listing.street, house_no=listing.house_no,
                                created_day=d, is_repost=True,
                            )
                    elif r < P_REMOVE + P_PRICE_CHANGE and listing.price is not None:
                        listing.price = new_price(listing.price, rng)
                elif not listing.reposted and rng.random() < P_RETURN:
                    listing.active = True

        # 2) Tin mới
        n_new = n_initial if d == 1 else rng.randint(*NEW_PER_DAY)
        for _ in range(n_new):
            counter += 1
            listing = random_listing(rng, f"RP-{counter:06d}", created_day=d)
            listings[listing.listing_id] = listing

    return list(listings.values())

def format_price(price, rng):
    """Viết giá theo nhiều kiểu như người đăng tin thật. price=None nghĩa là chưa có giá."""
    if price is None:
        return rng.choice(["Thỏa thuận", "Liên hệ"])
    millions, rest = divmod(price, 1_000_000)  # 3_500_000 -> (3, 500_000)
    styles = [
        (f"{price / 1_000_000:.1f} triệu/tháng", 25),
        (f"{price / 1_000_000:.1f}".replace(".", ",") + " triệu", 20),
        (f"{price / 1_000_000:.1f}tr", 15),
        (str(price), 10),
        (f"{price:,}".replace(",", ".") + "đ", 10),
        (f"{price // 1000}k", 12),
    ]
    if millions >= 1:
        styles.append((f"{millions}tr{rest // 100_000}" if rest else f"{millions}tr", 8))
    if rest == 500_000:
        styles.append((f"{millions} triệu rưỡi", 5))
    texts, weights = zip(*styles)
    return rng.choices(texts, weights=weights)[0]


def format_area(area, rng):
    """Diện tích cũng viết nhiều kiểu, đôi khi bị thiếu."""
    styles = [f"{area}m2", f"{area} m²", str(area), None]
    return rng.choices(styles, weights=[40, 30, 25, 5])[0]

def day_to_date(day):
    """Ngày 1 của mô phỏng là START_DATE, ngày 2 là hôm sau..."""
    return START_DATE + timedelta(days=day - 1)


def to_raw(listing, seed, snap_date):
    """Biến trạng thái THẬT của một tin thành dữ liệu THÔ (bẩn) như website hiển thị."""
    # Cách viết của MỘT tin phải ổn định giữa các ngày. Nên không dùng rng chung
    # của mô phỏng, mà dùng bộ ngẫu nhiên riêng có hạt giống lấy từ mã tin.
    static = random.Random(f"{seed}:{listing.listing_id}:static")
    price_rng = random.Random(f"{seed}:{listing.listing_id}:{listing.price}")

    district_raw = static.choices(
        [listing.district, f"Q. {listing.district}", listing.district.upper()],
        weights=[70, 15, 15],
    )[0]
    area_raw = format_area(listing.area, static)
    posted_at = datetime.combine(
        day_to_date(listing.created_day),
        time(static.randint(7, 22), static.randint(0, 59)),
    )
    title = f"{listing.ptype} {listing.area}m2 {listing.street} giá tốt"
    if listing.is_repost:
        title += " (đăng lại)"

    return {
        "listing_id": listing.listing_id,
        "title": title,
        "property_type": listing.ptype,
        "price_raw": format_price(listing.price, price_rng),
        "area_raw": area_raw,
        "district_raw": district_raw,
        "address_raw": f"Số {listing.house_no}, {listing.street}, {listing.district}",
        "posted_at": posted_at.isoformat(),
        "snapshot_date": snap_date.isoformat(),
        "source": "mock",
    }

def snapshot(day, seed=42, n_initial=30):
    """Những tin website hiển thị vào ngày `day` (ngày 1, 2, 3, ...)."""
    snap_date = day_to_date(day)
    records = [
        to_raw(listing, seed, snap_date)
        for listing in simulate(day, seed, n_initial)
        if listing.active
    ]
    random.Random(f"{seed}:order:{day}").shuffle(records)  # thứ tự không cố định
    return records

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