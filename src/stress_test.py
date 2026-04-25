"""
Stress testing and scenario comparison module.
Includes:
  - check_kpi_failure  — checks all KPIs including voice blocking
  - run_breaking_point_study — sweeps load until first KPI failure
  - run_scenario_comparison  — side-by-side baseline vs failure at current load
"""
import copy

from src.topology import build_topology, apply_failure
from src.traffic import generate_traffic
from src.routing import compute_routes
from src.wireless import evaluate_wireless
from src.backhaul import evaluate_backhaul
from src.qos import evaluate_qos


def check_kpi_failure(qos_results: dict, config: dict) -> list:
    """Return a list of KPI names that are currently failing."""
    targets = config["kpi_targets"]
    failures = []

    if qos_results["average_delay_ms"] > targets["max_delay_ms_critical"]:
        failures.append("critical_delay")

    if qos_results["packet_loss_percent"] > targets["max_packet_loss_percent"]:
        failures.append("packet_loss")

    if qos_results["throughput_mbps"] < targets["min_throughput_mbps"]:
        failures.append("throughput")

    if qos_results["site_availability_percent"] < targets["min_site_availability_percent"]:
        failures.append("site_availability")

    # Voice blocking probability (Erlang B) — requires teletraffic config
    if "voice_blocking_percent" in qos_results:
        max_blocking = targets.get("max_voice_blocking_percent", 2.0)
        if qos_results["voice_blocking_percent"] > max_blocking:
            failures.append("voice_blocking")

    return failures


def run_breaking_point_study(
    config: dict,
    max_multiplier: float = 5.0,
    step: float = 0.25,
) -> dict:
    """
    Sweep the load multiplier from 1.0 to max_multiplier.
    Stop and report when the first KPI failure occurs.
    Uses a deep copy so the caller's config dict is never mutated.
    """
    cfg = copy.deepcopy(config)
    multiplier = 1.0
    history = []

    while multiplier <= max_multiplier:
        cfg["load_multiplier"] = multiplier

        topology = build_topology(cfg)
        topology, failed_info = apply_failure(topology, cfg)
        traffic = generate_traffic(cfg)
        routes = compute_routes(topology, traffic, cfg)
        wireless_results = evaluate_wireless(cfg)
        backhaul_results = evaluate_backhaul(topology, cfg, failed_info)
        qos_results = evaluate_qos(
            traffic, routes, wireless_results, backhaul_results, cfg, failed_info
        )
        failures = check_kpi_failure(qos_results, cfg)

        history.append(
            {
                "load_multiplier": round(multiplier, 2),
                "qos_results": qos_results,
                "failures": failures,
            }
        )

        if failures:
            return {
                "first_failure_multiplier": round(multiplier, 2),
                "failed_kpis": failures,
                "history": history,
            }

        multiplier = round(multiplier + step, 2)

    return {
        "first_failure_multiplier": None,
        "failed_kpis": [],
        "history": history,
    }


def run_scenario_comparison(config: dict) -> dict:
    """
    Run the pipeline twice at the current load multiplier:
      1. Baseline — failure disabled
      2. Failure  — failure enabled (CORE1-CORE2 link removed)

    Both runs use deep copies, so the original config is unchanged.
    Returns baseline and failure QoS dicts plus the load multiplier used.
    """
    lm = config.get("load_multiplier", 1.0)

    def _run(failure_on: bool) -> dict:
        cfg = copy.deepcopy(config)
        cfg["failure"]["enabled"] = failure_on
        cfg["load_multiplier"] = lm

        topo = build_topology(cfg)
        topo, fi = apply_failure(topo, cfg)
        tr = generate_traffic(cfg)
        rt = compute_routes(topo, tr, cfg)
        wr = evaluate_wireless(cfg)
        bh = evaluate_backhaul(topo, cfg, fi)
        return evaluate_qos(tr, rt, wr, bh, cfg, fi)

    return {
        "baseline": _run(failure_on=False),
        "failure": _run(failure_on=True),
        "load_multiplier": lm,
    }
