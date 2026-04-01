import networkx as nx

def compute_setup_delay(graph, path, link_loads_bps, link_capacities_bps,
                        packet_size_bytes=1500, proc_delay_ms=1.0):
    if path is None:
        return float('inf')

    total_delay = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]

        prop_delay = graph[u][v].get('delay_ms', 5.0)

        link_key = (u, v) if (u, v) in link_loads_bps else (v, u)
        load = link_loads_bps.get(link_key, 0)
        cap = link_capacities_bps.get(link_key, 1e9)

        if load >= cap:
            queue_delay = float('inf')
        else:
            mu = cap / (packet_size_bytes * 8)
            lam = load / (packet_size_bytes * 8)
            queue_delay = 1 / (mu - lam) * 1000

        total_delay += prop_delay + queue_delay

    total_delay += len(path) * proc_delay_ms

    return total_delay