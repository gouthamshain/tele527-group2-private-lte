def evaluate_qos(traffic, routes, wireless_results, backhaul_results, config, failed_info=None):
    total_load = sum(item["offered_load"] for item in traffic)

    reachable_sites = sum(1 for r in routes.values() if r["reachable"])
    total_sites = len(routes)

    if reachable_sites > 0:
        avg_route_delay = sum(
            r["path_delay_ms"] for r in routes.values() if r["reachable"] and r["path_delay_ms"] is not None
        ) / reachable_sites
    else:
        avg_route_delay = 999

    failure_penalty = 0
    if failed_info and failed_info.get("failure_enabled"):
        failure_penalty = 15

    unreachable_penalty = (total_sites - reachable_sites) * 20

    average_delay_ms = 10 + (total_load * 0.3) + avg_route_delay + failure_penalty + unreachable_penalty
    average_jitter_ms = 2 + (total_load * 0.05) + (failure_penalty * 0.2)
    throughput_mbps = max(0, min(total_load * 1.2 - unreachable_penalty, 500))
    packet_loss_percent = 0.1

    if total_load > 100:
        packet_loss_percent += min((total_load - 100) * 0.02, 5.0)

    if failed_info and failed_info.get("failure_enabled"):
        packet_loss_percent += 1.5

    if total_sites > 0:
        site_availability_percent = (reachable_sites / total_sites) * 100
    else:
        site_availability_percent = 0

    return {
        "average_delay_ms": round(average_delay_ms, 2),
        "average_jitter_ms": round(average_jitter_ms, 2),
        "throughput_mbps": round(throughput_mbps, 2),
        "packet_loss_percent": round(packet_loss_percent, 2),
        "reachable_sites": reachable_sites,
        "total_sites": total_sites,
        "site_availability_percent": round(site_availability_percent, 2),
        "failure_active": failed_info.get("failure_enabled", False) if failed_info else False
    }