import networkx as nx


def compute_routes(graph, traffic, config):
    routes = {}

    core_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "core"]
    base_stations = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "base_station"]

    if not core_nodes:
        return routes

    destination = core_nodes[0]

    for bs in base_stations:
        try:
            path = nx.shortest_path(graph, bs, destination, weight="delay_ms")
            delay = 0
            for i in range(len(path) - 1):
                delay += graph[path[i]][path[i + 1]].get("delay_ms", 0)

            routes[bs] = {
                "path": path,
                "reachable": True,
                "path_delay_ms": delay
            }
        except nx.NetworkXNoPath:
            routes[bs] = {
                "path": None,
                "reachable": False,
                "path_delay_ms": None
            }

    return routes