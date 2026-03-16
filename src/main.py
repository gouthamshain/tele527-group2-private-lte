from src.config_loader import load_config
from src.topology import build_topology
from src.traffic import generate_traffic
from src.routing import compute_routes
from src.wireless import evaluate_wireless
from src.backhaul import evaluate_backhaul
from src.qos import evaluate_qos
from src.forecasting import forecast_traffic


def main():
    config = load_config("configs/scenario_group2.yaml")

    topology = build_topology(config)
    traffic = generate_traffic(config)
    routes = compute_routes(topology, traffic, config)
    wireless_results = evaluate_wireless(config)
    backhaul_results = evaluate_backhaul(topology, config)
    qos_results = evaluate_qos(traffic, routes, wireless_results, backhaul_results, config)
    forecast_results = forecast_traffic(traffic, config)

    print("Simulation complete.")
    print("QoS Results:", qos_results)
    print("Forecast Results:", forecast_results)


if __name__ == "__main__":
    main()