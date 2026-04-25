"""Tests for topology module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.topology import build_topology, apply_failure

BASE_CONFIG = {
    "network": {
        "base_stations": [{"id": "BS1"}, {"id": "BS2"}],
        "core_nodes": [{"id": "CORE1"}],
        "links": [
            {"from": "BS1", "to": "CORE1", "capacity_mbps": 100, "delay_ms": 5},
            {"from": "BS2", "to": "CORE1", "capacity_mbps": 100, "delay_ms": 6},
        ],
    },
    "failure": {"enabled": False, "failed_link": {"from": "BS1", "to": "CORE1"}},
}


def test_build_topology_node_count():
    g = build_topology(BASE_CONFIG)
    assert g.number_of_nodes() == 3  # BS1, BS2, CORE1


def test_build_topology_edge_count():
    g = build_topology(BASE_CONFIG)
    assert g.number_of_edges() == 2


def test_node_types():
    g = build_topology(BASE_CONFIG)
    assert g.nodes["BS1"]["node_type"] == "base_station"
    assert g.nodes["CORE1"]["node_type"] == "core"


def test_failure_disabled():
    g = build_topology(BASE_CONFIG)
    g, info = apply_failure(g, BASE_CONFIG)
    assert info["failure_enabled"] is False
    assert info["link_removed"] is False
    assert g.number_of_edges() == 2


def test_failure_enabled_removes_edge():
    cfg = dict(BASE_CONFIG)
    cfg["failure"] = {"enabled": True, "failed_link": {"from": "BS1", "to": "CORE1"}}
    g = build_topology(cfg)
    g, info = apply_failure(g, cfg)
    assert info["failure_enabled"] is True
    assert info["link_removed"] is True
    assert g.number_of_edges() == 1
