def evaluate_backhaul(graph, config: dict, failed_info: dict | None = None):
    results = []

    failed_link = None
    if failed_info:
        failed_link = failed_info.get("failed_link")

    for u, v, data in graph.edges(data=True):
        results.append({
            "link": f"{u}-{v}",
            "capacity_mbps": data.get("capacity_mbps", 0),
            "delay_ms": data.get("delay_ms", 0),
            "status": "active"
        })

    if failed_link and failed_info.get("failure_enabled"):
        u, v = failed_link
        if not failed_info.get("link_removed"):
            results.append({
                "link": f"{u}-{v}",
                "capacity_mbps": 0,
                "delay_ms": None,
                "status": "failed_requested_but_not_found"
            })
        else:
            results.append({
                "link": f"{u}-{v}",
                "capacity_mbps": 0,
                "delay_ms": None,
                "status": "failed"
            })

    return results