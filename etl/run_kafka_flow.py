"""Chạy luồng Kafka từ đầu đến cuối bằng một lệnh.

Bronze -> Kafka (listing.events) -> raw.listings -> Staging/Core -> Kafka (listing.price_changes)
Dừng ngay ở bước đầu tiên lỗi, thoát mã 1.
"""
import argparse
import logging

from etl import consume_events, publish_batch, publish_price_changes, run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("run_kafka_flow")


def run_step(name, func, argv):
    """Chạy một bước. Trả về True nếu thành công (kể cả khi bước trả None)."""
    log.info("=== %s ===", name)
    try:
        result = func(argv)
    except SystemExit as exc:
        if exc.code in (0, None):
            return True
        log.error("Bước '%s' thất bại (mã %s)", name, exc.code)
        return False
    if isinstance(result, int) and result != 0:
        log.error("Bước '%s' thất bại (mã %s)", name, result)
        return False
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Luồng Kafka end-to-end")
    parser.add_argument(
        "--since",
        help="Chỉ phát event đổi giá từ ngày này (YYYY-MM-DD); mặc định phát tất cả",
    )
    args = parser.parse_args(argv)

    price_argv = ["--since", args.since] if args.since else []
    steps = [
        ("1. Bronze -> Kafka (batch mới)", publish_batch.main, ["--only-new"]),
        ("2. Kafka -> raw.listings", consume_events.main, ["--once"]),
        ("3. Raw -> Staging -> Core", run_pipeline.main, ["--skip-bronze"]),
        ("4. Phát event đổi giá", publish_price_changes.main, price_argv),
    ]
    for name, func, step_argv in steps:
        if not run_step(name, func, step_argv):
            return 1
    log.info("Luồng Kafka hoàn tất")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())