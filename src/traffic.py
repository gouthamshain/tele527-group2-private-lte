def generate_traffic(config: dict):
    traffic_classes = config["traffic_classes"]
    traffic = []

    for cls in traffic_classes:
        traffic.append({
            "class": cls["name"],
            "offered_load": cls["offered_load"],
            "priority": cls["priority"]
        })

    return traffic