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