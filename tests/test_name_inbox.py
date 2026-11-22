import json
import os

from scripts import name_inbox

T0 = 1795368249  # 23/11/2026 00:24 giờ Việt Nam (đã sang ngày mới theo UTC thì vẫn phải ra 23)


def nhatot_page(ids):
    ads = [{"list_id": i, "subject": "x"} for i in ids]
    data = {"props": {"initialState": {"adlisting": {"data": {"ads": ads}}}}}
    return ('<html><head><link rel="canonical" href="https://www.nhatot.com/thue-phong-tro-ha-noi"/></head>'
            f'<body><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></body></html>')


def batdongsan_page(ids):
    cards = "".join(f'<div class="js__card js__card-full-web" prid="{i}"></div>' for i in ids)
    return ('<html><head><link rel="canonical" href="https://batdongsan.com.vn/cho-thue-nha-tro-phong-tro-ha-noi"/>'
            f'</head><body>{cards}</body></html>')


def save(folder, name, html, mtime):
    path = folder / name
    path.write_text(html, encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path, mtime


def test_detect_source():
    assert name_inbox.detect_source(nhatot_page([1])) == "nhatot"
    assert name_inbox.detect_source(batdongsan_page([1])) == "batdongsan"
    assert name_inbox.detect_source("<html></html>") is None


def test_pages_are_numbered_by_save_order_and_dated_in_vietnam_time(tmp_path):
    files = [save(tmp_path, "b.html", nhatot_page([4, 5]), T0 + 2),
             save(tmp_path, "a.html", nhatot_page([1, 2, 3]), T0 + 1),
             save(tmp_path, "c.html", nhatot_page([6]), T0 + 3)]
    renames, errors = name_inbox.plan(files, 3)
    assert errors == []
    assert [(p.name, n) for p, n in renames] == [
        ("a.html", "nhatot_2026-11-23.html"),
        ("b.html", "nhatot_2026-11-23_p2.html"),
        ("c.html", "nhatot_2026-11-23_p3.html")]


def test_wrong_page_count_is_rejected(tmp_path):
    files = [save(tmp_path, "a.html", batdongsan_page([1]), T0), save(tmp_path, "b.html", batdongsan_page([2]), T0 + 1)]
    _, errors = name_inbox.plan(files, 3)
    assert any("có 2 trang, cần đúng 3" in e for e in errors)


def test_same_page_saved_twice_is_rejected(tmp_path):
    files = [save(tmp_path, "a.html", nhatot_page([1, 2]), T0), save(tmp_path, "b.html", nhatot_page([2, 3]), T0 + 1)]
    _, errors = name_inbox.plan(files, 2)
    assert any("trùng tin" in e for e in errors)


def test_unknown_page_is_rejected(tmp_path):
    _, errors = name_inbox.plan([save(tmp_path, "x.html", "<html>hello</html>", T0)], 1)
    assert any("không nhận ra nguồn" in e for e in errors)