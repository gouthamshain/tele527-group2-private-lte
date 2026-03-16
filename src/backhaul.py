def evaluate_backhaul(graph, config: dict):
    results = []

    for u, v, data in graph.edges(data=True):
        results.append({
            "link": f"{u}-{v}",
            "capacity_mbps": data.get("capacity_mbps", 0),
            "delay_ms": data.get("delay_ms", 0)
        })

    return results