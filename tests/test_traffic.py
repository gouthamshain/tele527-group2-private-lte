"""Tests for traffic generation module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.traffic import generate_traffic

BASE_CONFIG = {
    "traffic_classes": [
        {"name": "alarms_control", "offered_load": 20, "priority": 1},
        {"name": "voice",          "offered_load": 60, "priority": 2},
    ],
    "load_multiplier": 1.0,
}


def test_traffic_count():
    t = generate_traffic(BASE_CONFIG)
    assert len(t) == 2


def test_traffic_load_at_1x():
    t = generate_traffic(BASE_CONFIG)
    assert t[0]["offered_load"] == 20.0
    assert t[1]["offered_load"] == 60.0


def test_traffic_load_scaled():
    cfg = {**BASE_CONFIG, "load_multiplier": 2.0}
    t = generate_traffic(cfg)
    assert t[0]["offered_load"] == 40.0
    assert t[1]["offered_load"] == 120.0


def test_traffic_priority_preserved():
    t = generate_traffic(BASE_CONFIG)
    assert t[0]["priority"] == 1
    assert t[1]["priority"] == 2


def test_traffic_class_names():
    t = generate_traffic(BASE_CONFIG)
    names = [item["class"] for item in t]
    assert "alarms_control" in names
    assert "voice" in names
