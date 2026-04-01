import networkx as nx


def build_topology(config: dict):
    graph = nx.Graph()

    base_stations = config["network"]["base_stations"]
    core_nodes = config["network"]["core_nodes"]

    for bs in base_stations:
        graph.add_node(bs["id"], node_type="base_station")

    for core in core_nodes:
        graph.add_node(core["id"], node_type="core")

    for link in config["network"]["links"]:
        graph.add_edge(
            link["from"],
            link["to"],
            capacity_mbps=link["capacity_mbps"],
            delay_ms=link["delay_ms"]
        )

    return graph


def apply_failure(graph, config: dict):
    failure_cfg = config.get("failure", {})
    enabled = failure_cfg.get("enabled", False)

    failed_info = {
        "failure_enabled": enabled,
        "failed_link": None,
        "link_removed": False
    }

    if not enabled:
        return graph, failed_info

    failed_link = failure_cfg.get("failed_link", {})
    u = failed_link.get("from")
    v = failed_link.get("to")

    failed_info["failed_link"] = (u, v)

    if u and v and graph.has_edge(u, v):
        graph.remove_edge(u, v)
        failed_info["link_removed"] = True

    return graph, failed_info