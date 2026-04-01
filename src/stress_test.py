from src.topology import build_topology, apply_failure
from src.traffic import generate_traffic
from src.routing import compute_routes
from src.wireless import evaluate_wireless
from src.backhaul import evaluate_backhaul
from src.qos import evaluate_qos


def check_kpi_failure(qos_results: dict, config: dict):
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

    return failures


def run_breaking_point_study(config: dict, max_multiplier: float = 5.0, step: float = 0.25):
    multiplier = 1.0
    history = []

    while multiplier <= max_multiplier:
        config["load_multiplier"] = multiplier

        topology = build_topology(config)
        topology, failed_info = apply_failure(topology, config)

        traffic = generate_traffic(config)
        routes = compute_routes(topology, traffic, config)
        wireless_results = evaluate_wireless(config)
        backhaul_results = evaluate_backhaul(topology, config, failed_info)
        qos_results = evaluate_qos(traffic, routes, wireless_results, backhaul_results, config, failed_info)

        failures = check_kpi_failure(qos_results, config)

        history.append({
            "load_multiplier": round(multiplier, 2),
            "qos_results": qos_results,
            "failures": failures
        })

        if failures:
            return {
                "first_failure_multiplier": round(multiplier, 2),
                "failed_kpis": failures,
                "history": history
            }

        multiplier += step

    return {
        "first_failure_multiplier": None,
        "failed_kpis": [],
        "history": history
    }