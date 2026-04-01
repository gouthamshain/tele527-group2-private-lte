def generate_traffic(config: dict):
    traffic_classes = config["traffic_classes"]
    load_multiplier = config.get("load_multiplier", 1.0)

    traffic = []
    for cls in traffic_classes:
        traffic.append({
            "class": cls["name"],
            "offered_load": cls["offered_load"] * load_multiplier,
            "priority": cls["priority"]
        })

    return traffic