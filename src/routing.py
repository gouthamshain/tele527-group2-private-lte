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
            routes[bs] = path
        except nx.NetworkXNoPath:
            routes[bs] = None

    return routes