from src.config_loader import load_config
from src.topology import build_topology
from src.traffic import generate_traffic
from src.routing import compute_routes
from src.wireless import evaluate_wireless
from src.backhaul import evaluate_backhaul
from src.qos import evaluate_qos
from src.forecasting import forecast_traffic
from src.signaling import compute_setup_delay
import matplotlib.pyplot as plt
import numpy as np

def main():
    config = load_config("configs/scenario_group2.yaml")
    topology = build_topology(config)
    traffic = generate_traffic(config)
    routes = compute_routes(topology, traffic, config)

    print("\n=== Routing Table ===")
    for bs, path in routes.items():
        print(f"{bs} -> CORE1: {path}")

    def compute_link_loads(graph, routes, traffic_classes):
        link_loads = {}
        for u, v in graph.edges():
            link_loads[(u, v)] = 0
            link_loads[(v, u)] = 0
        for bs, path in routes.items():
            if path is None:
                continue
            total_load_mbps = sum(tc.get('offered_load', 0) for tc in traffic_classes)
            total_load_bps = total_load_mbps * 1e6
            for i in range(len(path)-1):
                u, v = path[i], path[i+1]
                link_loads[(u, v)] += total_load_bps
                link_loads[(v, u)] += total_load_bps
        return link_loads

    traffic_classes = config.get('traffic_classes', [])
    link_loads = compute_link_loads(topology, routes, traffic_classes)

    link_capacities = {}
    for link in config['network']['links']:
        u, v = link['from'], link['to']
        cap_bps = link['capacity_mbps'] * 1e6
        link_capacities[(u, v)] = cap_bps
        link_capacities[(v, u)] = cap_bps

    setup_delays = {}
    for bs, path in routes.items():
        if path:
            delay = compute_setup_delay(topology, path, link_loads, link_capacities)
            setup_delays[bs] = delay
        else:
            setup_delays[bs] = float('inf')

    print("\n=== Call Setup Delays (ms) ===")
    for bs, delay in setup_delays.items():
        print(f"{bs}: {delay:.2f} ms")

    test_bs = 'BS3'
    path = routes.get(test_bs)
    if path:
        load_factors = np.linspace(0.2, 1.5, 20)
        delays = []
        for factor in load_factors:
            scaled_loads = {link: load * factor for link, load in link_loads.items()}
            delay = compute_setup_delay(topology, path, scaled_loads, link_capacities)
            delays.append(delay)
        plt.figure()
        plt.plot(load_factors, delays, marker='o')
        plt.xlabel('Load Factor (multiples of baseline)')
        plt.ylabel('Call Setup Delay (ms)')
        plt.title(f'Setup Delay for {test_bs} → CORE1')
        plt.grid(True)
        plt.savefig('setup_delay_vs_load.png')
        plt.close()
    else:
        print(f"No path for {test_bs}")

    baseline_delays = setup_delays.copy()
    topology_fail = topology.copy()
    topology_fail.remove_edge('BS3', 'CORE2')
    routes_fail = compute_routes(topology_fail, traffic, config)
    link_loads_fail = compute_link_loads(topology_fail, routes_fail, traffic_classes)
    setup_delays_fail = {}
    for bs, path in routes_fail.items():
        if path:
            delay = compute_setup_delay(topology_fail, path, link_loads_fail, link_capacities)
            setup_delays_fail[bs] = delay
        else:
            setup_delays_fail[bs] = float('inf')

    print("\n=== Failure Comparison (BS3) ===")
    print(f"Baseline delay: {baseline_delays.get('BS3'):.2f} ms")
    print(f"After failure:  {setup_delays_fail.get('BS3'):.2f} ms")

    wireless_results = evaluate_wireless(config)
    backhaul_results = evaluate_backhaul(topology, config)
    qos_results = evaluate_qos(traffic, routes, wireless_results, backhaul_results, config)
    forecast_results = forecast_traffic(traffic, config)

    print("\nSimulation complete.")
    print("QoS Results:", qos_results)
    print("Forecast Results:", forecast_results)

if __name__ == "__main__":
    main()