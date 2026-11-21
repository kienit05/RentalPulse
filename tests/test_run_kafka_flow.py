"""Test thứ tự và hành vi dừng-khi-lỗi của run_kafka_flow (không cần Kafka hay DB)."""
import pytest

from etl import consume_events, publish_batch, publish_price_changes, run_kafka_flow, run_pipeline


@pytest.fixture
def calls(monkeypatch):
    recorded = []

    def make_fake(name, outcome=None):
        def fake(argv=None):
            recorded.append((name, list(argv or [])))
            if outcome == "exit1":
                raise SystemExit(1)
            if outcome == "return1":
                return 1
        return fake

    def install(**outcomes):
        monkeypatch.setattr(publish_batch, "main", make_fake("publish_batch", outcomes.get("publish_batch")))
        monkeypatch.setattr(consume_events, "main", make_fake("consume_events", outcomes.get("consume_events")))
        monkeypatch.setattr(run_pipeline, "main", make_fake("run_pipeline", outcomes.get("run_pipeline")))
        monkeypatch.setattr(
            publish_price_changes, "main", make_fake("publish_price_changes", outcomes.get("publish_price_changes"))
        )
        return recorded

    return install


def test_steps_run_in_order_with_expected_arguments(calls):
    recorded = calls()
    assert run_kafka_flow.main([]) == 0
    assert recorded == [
        ("publish_batch", ["--only-new"]),
        ("consume_events", ["--once"]),
        ("run_pipeline", ["--skip-bronze"]),
        ("publish_price_changes", []),
    ]


def test_since_is_passed_only_to_price_step(calls):
    recorded = calls()
    run_kafka_flow.main(["--since", "2026-11-21"])
    assert recorded[-1] == ("publish_price_changes", ["--since", "2026-11-21"])
    assert recorded[0] == ("publish_batch", ["--only-new"])


def test_stops_at_first_failing_step_with_system_exit(calls):
    recorded = calls(consume_events="exit1")
    assert run_kafka_flow.main([]) == 1
    assert [name for name, _ in recorded] == ["publish_batch", "consume_events"]


def test_stops_when_step_returns_nonzero(calls):
    recorded = calls(run_pipeline="return1")
    assert run_kafka_flow.main([]) == 1
    assert [name for name, _ in recorded][-1] == "run_pipeline"
    assert "publish_price_changes" not in [name for name, _ in recorded]