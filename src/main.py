from src.config_loader import load_config
from src.topology import build_topology, apply_failure
from src.traffic import generate_traffic
from src.routing import compute_routes
from src.wireless import evaluate_wireless
from src.backhaul import evaluate_backhaul
from src.qos import evaluate_qos
from src.forecasting import forecast_traffic
from src.stress_test import run_breaking_point_study
from src.plotting import plot_stress_test_results


def main():
    config = load_config("configs/scenario_group2.yaml")

    topology = build_topology(config)
    topology, failed_info = apply_failure(topology, config)

    traffic = generate_traffic(config)
    routes = compute_routes(topology, traffic, config)
    wireless_results = evaluate_wireless(config)
    backhaul_results = evaluate_backhaul(topology, config, failed_info)
    qos_results = evaluate_qos(traffic, routes, wireless_results, backhaul_results, config, failed_info)
    forecast_results = forecast_traffic(traffic, config)
    stress_results = run_breaking_point_study(config)

    scenario_name = "failure" if failed_info.get("failure_enabled") else "baseline"
    plot_stress_test_results(stress_results, scenario_name=scenario_name)

    print("Simulation complete.")
    print("Failure Info:", failed_info)
    print("Routes:", routes)
    print("Backhaul Results:", backhaul_results)
    print("QoS Results:", qos_results)
    print("Forecast Results:", forecast_results)
    print("Stress Test Results:", stress_results)


if __name__ == "__main__":
    main()