"""
Signaling and call setup delay module.
Provides per-hop M/D/1 queue delay model for call setup latency estimation
and a burst-sweep study to show how setup delay grows under load.
"""
import networkx as nx


def compute_setup_delay(
    graph,
    path,
    link_loads_bps: dict,
    link_capacities_bps: dict,
    packet_size_bytes: int = 1500,
    proc_delay_ms: float = 1.0,
) -> float:
    """
    Estimate call setup delay along a path using an M/D/1 queuing model
    at each hop, plus propagation delay and per-node processing delay.

    Returns total delay in milliseconds, or float('inf') if any link is saturated.
    """
    if path is None:
        return float("inf")

    total_delay = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]

        prop_delay = graph[u][v].get("delay_ms", 5.0)

        link_key = (u, v) if (u, v) in link_loads_bps else (v, u)
        load = link_loads_bps.get(link_key, 0)
        cap = link_capacities_bps.get(link_key, 1e9)

        if load >= cap:
            return float("inf")

        # M/D/1 queue delay: service rate mu (packets/s), arrival rate lam (packets/s)
        mu = cap / (packet_size_bytes * 8)
        lam = load / (packet_size_bytes * 8)
        queue_delay = 1.0 / (mu - lam) * 1000.0  # ms

        total_delay += prop_delay + queue_delay

    # Per-node processing delay (one per node in path)
    total_delay += len(path) * proc_delay_ms

    return total_delay


def compute_signaling_results(graph, routes: dict, traffic: list, config: dict) -> dict:
    """
    Integrate signaling into the main pipeline.

    Computes:
      1. Per-base-station call setup delay at the current offered load.
      2. A burst sweep showing how setup delay grows as load factor increases
         for the reference base station (first reachable BS).

    Link loads are approximated by distributing total offered traffic
    uniformly across all bidirectional links — a conservative model
    suitable for a balanced industrial LTE network.
    """
    sig_cfg = config.get("signaling", {})
    pkt_size = sig_cfg.get("packet_size_bytes", 1500)
    proc_ms = sig_cfg.get("proc_delay_ms", 1.0)
    burst_multipliers: list = sig_cfg.get(
        "burst_multipliers", [round(0.2 * i, 1) for i in range(1, 11)]
    )

    # Build link capacity table from graph
    link_capacities_bps: dict = {}
    for u, v, data in graph.edges(data=True):
        cap = data.get("capacity_mbps", 100) * 1e6
        link_capacities_bps[(u, v)] = cap
        link_capacities_bps[(v, u)] = cap

    # Distribute total offered load uniformly across links
    total_load_bps = sum(t["offered_load"] for t in traffic) * 1e6
    n_links = max(1, len(link_capacities_bps) // 2)
    base_load_per_link = total_load_bps / n_links
    base_link_loads: dict = {k: base_load_per_link for k in link_capacities_bps}

    # ── Per-BS setup delay at current load ──────────────────────────────────
    per_bs: list = []
    for bs, route in routes.items():
        path = route.get("path")
        delay = compute_setup_delay(
            graph, path, base_link_loads, link_capacities_bps, pkt_size, proc_ms
        )
        per_bs.append(
            {
                "base_station": bs,
                "path": " -> ".join(path) if path else "No path",
                "hops": len(path) - 1 if path else 0,
                "setup_delay_ms": round(delay, 4) if delay != float("inf") else None,
            }
        )

    # ── Burst sweep for ALL reachable base stations ─────────────────────────
    burst_sweep: list = []
    reachable_bs = [bs for bs, r in routes.items() if r.get("reachable")]

    for bs in reachable_bs:
        path = routes[bs].get("path")
        for bm in burst_multipliers:
            burst_loads = {k: v * bm for k, v in base_link_loads.items()}
            d = compute_setup_delay(
                graph, path, burst_loads, link_capacities_bps, pkt_size, proc_ms
            )
            burst_sweep.append(
                {
                    "load_factor": bm,
                    "base_station": bs,
                    "setup_delay_ms": round(d, 4) if d != float("inf") else None,
                }
            )

    ref_bs = reachable_bs[0] if reachable_bs else None

    return {
        "per_bs_delays": per_bs,
        "burst_sweep": burst_sweep,
        "reference_bs": ref_bs,
    }
