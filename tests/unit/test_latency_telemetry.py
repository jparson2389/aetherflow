from aetherflow.input.mapping import InputLatencyTelemetry


def test_record_and_mean() -> None:
    t = InputLatencyTelemetry()
    t.record(1_000_000)  # 1 ms
    t.record(3_000_000)  # 3 ms
    assert t.mean_ms == 2.0
    assert t.sample_count == 2


def test_p99_with_known_distribution() -> None:
    t = InputLatencyTelemetry()
    for i in range(1, 101):
        t.record(i * 1_000_000)  # 1ms..100ms
    assert t.p99_ms >= 99.0


def test_empty_telemetry_returns_zero() -> None:
    t = InputLatencyTelemetry()
    assert t.mean_ms == 0.0
    assert t.p99_ms == 0.0
    assert t.sample_count == 0


def test_window_eviction() -> None:
    t = InputLatencyTelemetry(window_size=4)
    for i in range(6):
        t.record((i + 1) * 1_000_000)
    assert t.sample_count == 4


def test_reset_clears_samples() -> None:
    t = InputLatencyTelemetry()
    t.record(1_000_000)
    t.reset()
    assert t.sample_count == 0
    assert t.mean_ms == 0.0
