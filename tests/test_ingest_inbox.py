import pytest

from collectors import collector
from etl import ingest_inbox, run_pipeline


@pytest.mark.parametrize("name, expected", [
    ("nhatot_2026-11-21.html", ("nhatot", "2026-11-21", 1)),
    ("batdongsan_2026-01-05.html", ("batdongsan", "2026-01-05", 1)),
    ("nhatot_2026-11-21_p2.html", ("nhatot", "2026-11-21", 2)),
    ("batdongsan_2026-11-21_p15.html", ("batdongsan", "2026-11-21", 15)),
    ("nhatot_2026-11-21_p0.html", None),    # không có trang 0
    ("nhatot_2026-11-21_2.html", None),     # thiếu chữ p
    ("nhatot_2026-13-40.html", None),       # ngày không tồn tại
    ("nhatot_21-11-2026.html", None),       # sai định dạng ngày
    ("chotot_2026-11-21.html", None),       # nguồn lạ
    ("nhatot_2026-11-21.htm", None),        # sai đuôi
    ("nhatot.html", None),
])
def test_parse_name(name, expected):
    assert ingest_inbox.parse_name(name) == expected


def test_page_url():
    assert ingest_inbox.page_url("nhatot", 1) == "https://www.nhatot.com/thue-phong-tro-ha-noi"
    assert ingest_inbox.page_url("nhatot", 3) == "https://www.nhatot.com/thue-phong-tro-ha-noi?page=3"
    assert ingest_inbox.page_url("batdongsan", 2).endswith("/cho-thue-nha-tro-phong-tro-ha-noi/p2?sortValue=8")


@pytest.fixture
def env(tmp_path, monkeypatch):
    inbox, processed = tmp_path / "inbox", tmp_path / "processed"
    inbox.mkdir()
    monkeypatch.setattr(ingest_inbox, "INBOX", inbox)
    monkeypatch.setattr(ingest_inbox, "PROCESSED", processed)
    calls = []
    monkeypatch.setattr(collector, "main", lambda argv: calls.append(argv))
    pipeline_runs = []
    monkeypatch.setattr(run_pipeline, "main", lambda argv=None: pipeline_runs.append(argv))
    return inbox, processed, calls, pipeline_runs


def test_pending_files_are_ordered_by_date_source_then_page(env):
    inbox, *_ = env
    for name in ("nhatot_2026-11-22.html", "nhatot_2026-11-21_p10.html", "nhatot_2026-11-21_p2.html",
                 "nhatot_2026-11-21.html", "batdongsan_2026-11-21.html"):
        (inbox / name).write_text("x")
    names = [p.name for p, *_ in ingest_inbox.find_pending(inbox)]
    assert names == ["batdongsan_2026-11-21.html", "nhatot_2026-11-21.html",
                     "nhatot_2026-11-21_p2.html", "nhatot_2026-11-21_p10.html",
                     "nhatot_2026-11-22.html"]


def test_page_url_is_passed_to_collector(env):
    inbox, _, calls, _ = env
    (inbox / "nhatot_2026-11-21_p3.html").write_text("x")
    ingest_inbox.main(["--no-pipeline"])
    argv = calls[0]
    assert argv[argv.index("--url") + 1] == "https://www.nhatot.com/thue-phong-tro-ha-noi?page=3"


def test_successful_file_is_ingested_moved_and_pipeline_runs_once(env):
    inbox, processed, calls, pipeline_runs = env
    (inbox / "nhatot_2026-11-21.html").write_text("x")
    (inbox / "batdongsan_2026-11-21.html").write_text("x")
    ingest_inbox.main([])
    assert [c[1] for c in calls] == ["batdongsan", "nhatot"]
    assert all(c[-2:] == ["--snapshot-date", "2026-11-21"] for c in calls)
    assert sorted(p.name for p in processed.iterdir()) == [
        "batdongsan_2026-11-21.html", "nhatot_2026-11-21.html"]
    assert list(inbox.iterdir()) == []
    assert len(pipeline_runs) == 1


def test_failed_file_stays_in_inbox_and_exit_code_is_1(env, monkeypatch):
    inbox, processed, calls, pipeline_runs = env
    (inbox / "nhatot_2026-11-21.html").write_text("x")
    (inbox / "batdongsan_2026-11-21.html").write_text("x")

    def flaky(argv):
        calls.append(argv)
        if argv[1] == "nhatot":
            raise SystemExit(1)

    monkeypatch.setattr(collector, "main", flaky)
    with pytest.raises(SystemExit) as exc:
        ingest_inbox.main([])
    assert exc.value.code == 1
    assert (inbox / "nhatot_2026-11-21.html").exists()
    assert (processed / "batdongsan_2026-11-21.html").exists()
    assert len(pipeline_runs) == 1          # file tốt vẫn được đưa vào ETL


def test_badly_named_file_is_ignored(env):
    inbox, _, calls, pipeline_runs = env
    (inbox / "trang_moi.html").write_text("x")
    ingest_inbox.main([])
    assert calls == [] and pipeline_runs == []
    assert (inbox / "trang_moi.html").exists()


def test_no_pipeline_flag_skips_etl(env):
    inbox, _, calls, pipeline_runs = env
    (inbox / "nhatot_2026-11-21.html").write_text("x")
    ingest_inbox.main(["--no-pipeline"])
    assert len(calls) == 1 and pipeline_runs == []