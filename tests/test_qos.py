"""Tests for QoS evaluation and Erlang B."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.teletraffic import erlang_b, erlang_b_channels
from src.qos import evaluate_qos
from src.topology import build_topology, apply_failure
from src.routing import compute_routes
from src.traffic import generate_traffic

# ── Erlang B unit tests ────────────────────────────────────────────────────

def test_erlang_b_zero_traffic():
    assert erlang_b(0, 10) == 0.0


def test_erlang_b_zero_channels():
    assert erlang_b(5.0, 0) == 1.0


def test_erlang_b_blocking_decreases_with_more_channels():
    a = 8.0
    b10 = erlang_b(a, 10)
    b15 = erlang_b(a, 15)
    b20 = erlang_b(a, 20)
    assert b10 > b15 > b20


def test_erlang_b_channels_meets_target():
    a = 8.0
    target = 0.02
    n = erlang_b_channels(a, target)
    assert erlang_b(a, n) <= target
    # one fewer channel should exceed target
    assert erlang_b(a, n - 1) > target


# ── QoS integration smoke test ─────────────────────────────────────────────

_CFG = {
    "network": {
        "base_stations": [{"id": "BS1"}, {"id": "BS2"}],
        "core_nodes": [{"id": "CORE1"}],
        "links": [
            {"from": "BS1", "to": "CORE1", "capacity_mbps": 100, "delay_ms": 5},
            {"from": "BS2", "to": "CORE1", "capacity_mbps": 100, "delay_ms": 6},
        ],
    },
    "failure": {"enabled": False, "failed_link": {"from": "BS1", "to": "CORE1"}},
    "traffic_classes": [
        {"name": "voice", "offered_load": 60, "priority": 2},
    ],
    "load_multiplier": 1.0,
    "wireless": {
        "frequency_mhz": 1800, "base_height_m": 30, "mobile_height_m": 1.5,
        "sample_distances_km": [1.0], "tx_power_dbm": 46,
        "antenna_gain_dbi": 17, "cable_loss_db": 2, "rx_sensitivity_dbm": -95,
    },
    "teletraffic": {"voice_erlangs": 8.0, "voice_channels": 15, "target_blocking_percent": 2.0},
}


def _build_qos(cfg, failure_on=False):
    from src.wireless import evaluate_wireless
    c = dict(cfg)
    c["failure"]["enabled"] = failure_on
    g = build_topology(c)
    g, fi = apply_failure(g, c)
    tr = generate_traffic(c)
    rt = compute_routes(g, tr, c)
    wr = evaluate_wireless(c)
    return evaluate_qos(tr, rt, wr, [], c, fi)


def test_qos_keys_present():
    q = _build_qos(_CFG)
    for key in ("average_delay_ms", "throughput_mbps", "packet_loss_percent",
                 "site_availability_percent", "voice_blocking_percent"):
        assert key in q


def test_qos_full_availability_no_failure():
    q = _build_qos(_CFG)
    assert q["site_availability_percent"] == 100.0


def test_qos_availability_drops_on_failure():
    q = _build_qos(_CFG, failure_on=True)
    assert q["site_availability_percent"] < 100.0
