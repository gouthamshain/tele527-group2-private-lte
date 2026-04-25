"""
Microwave backhaul evaluation module.
Computes link capacity / delay status AND a full microwave link budget
(EIRP, free-space path loss, received signal level, fade margin).
"""
import math


def free_space_path_loss(freq_ghz: float, dist_km: float) -> float:
    """
    Free-space path loss in dB.
    FSPL = 20*log10(f_GHz) + 20*log10(d_km) + 92.45
    """
    return 20 * math.log10(freq_ghz) + 20 * math.log10(dist_km) + 92.45


def compute_link_budget(link: dict) -> dict:
    """
    Compute a complete point-to-point microwave link budget.

    Inputs (from YAML backhaul.microwave_links entry):
        tx_power_dbm, tx_antenna_gain_dbi, rx_antenna_gain_dbi,
        cable_loss_db, frequency_ghz, distance_km,
        rx_sensitivity_dbm, fade_margin_db

    Returns EIRP, FSPL, RSL, available margin, net margin, status.
    """
    tx_pwr = link["tx_power_dbm"]
    tx_gain = link["tx_antenna_gain_dbi"]
    rx_gain = link["rx_antenna_gain_dbi"]
    cable = link["cable_loss_db"]
    freq = link["frequency_ghz"]
    dist = link["distance_km"]
    rx_sens = link["rx_sensitivity_dbm"]
    fade = link["fade_margin_db"]

    fspl = free_space_path_loss(freq, dist)
    eirp = tx_pwr + tx_gain - cable
    rsl = eirp - fspl + rx_gain
    available_margin = rsl - rx_sens
    net_margin = available_margin - fade

    return {
        "fspl_db": round(fspl, 2),
        "eirp_dbm": round(eirp, 2),
        "rsl_dbm": round(rsl, 2),
        "available_margin_db": round(available_margin, 2),
        "net_margin_db": round(net_margin, 2),
        "budget_status": "PASS" if net_margin >= 0 else "FAIL",
    }


def evaluate_backhaul(graph, config: dict, failed_info: dict | None = None) -> list:
    """
    Evaluate all backhaul links.
    Merges graph-level capacity/delay data with full microwave link budget
    from the YAML backhaul.microwave_links section.
    """
    # Build lookup from the YAML microwave link definitions
    mw_links = config.get("backhaul", {}).get("microwave_links", [])
    mw_lookup: dict = {}
    for ml in mw_links:
        key_fwd = (ml["from"], ml["to"])
        key_rev = (ml["to"], ml["from"])
        mw_lookup[key_fwd] = ml
        mw_lookup[key_rev] = ml

    failed_link = None
    if failed_info:
        failed_link = failed_info.get("failed_link")

    results = []

    for u, v, data in graph.edges(data=True):
        is_failed = (
            failed_link is not None
            and failed_info.get("failure_enabled")
            and ((u, v) == failed_link or (v, u) == failed_link)
        )

        entry: dict = {
            "link": f"{u}-{v}",
            "from": u,
            "to": v,
            "capacity_mbps": data.get("capacity_mbps", 0),
            "delay_ms": data.get("delay_ms", 0),
            "status": "failed" if is_failed else "active",
        }

        # Enrich with link budget when microwave parameters are available
        ml = mw_lookup.get((u, v)) or mw_lookup.get((v, u))
        if ml:
            budget = compute_link_budget(ml)
            entry.update(
                {
                    "frequency_ghz": ml["frequency_ghz"],
                    "distance_km": ml["distance_km"],
                    "tx_power_dbm": ml["tx_power_dbm"],
                    "eirp_dbm": budget["eirp_dbm"],
                    "fspl_db": budget["fspl_db"],
                    "rsl_dbm": budget["rsl_dbm"],
                    "rx_sensitivity_dbm": ml["rx_sensitivity_dbm"],
                    "available_margin_db": budget["available_margin_db"],
                    "fade_margin_db": ml["fade_margin_db"],
                    "net_margin_db": budget["net_margin_db"],
                    "budget_status": budget["budget_status"],
                }
            )

        results.append(entry)

    # If the failed link was removed from the graph, add it explicitly
    # so operators can see it in the dashboard table
    if failed_link and failed_info.get("failure_enabled") and failed_info.get("link_removed"):
        u, v = failed_link
        already_listed = any(
            r["from"] == u and r["to"] == v for r in results
        )
        if not already_listed:
            entry = {
                "link": f"{u}-{v}",
                "from": u,
                "to": v,
                "capacity_mbps": 0,
                "delay_ms": None,
                "status": "failed",
            }
            ml = mw_lookup.get((u, v)) or mw_lookup.get((v, u))
            if ml:
                budget = compute_link_budget(ml)
                entry.update(
                    {
                        "frequency_ghz": ml["frequency_ghz"],
                        "distance_km": ml["distance_km"],
                        "tx_power_dbm": ml["tx_power_dbm"],
                        "eirp_dbm": budget["eirp_dbm"],
                        "fspl_db": budget["fspl_db"],
                        "rsl_dbm": budget["rsl_dbm"],
                        "rx_sensitivity_dbm": ml["rx_sensitivity_dbm"],
                        "available_margin_db": budget["available_margin_db"],
                        "fade_margin_db": ml["fade_margin_db"],
                        "net_margin_db": budget["net_margin_db"],
                        "budget_status": budget["budget_status"],
                    }
                )
            results.append(entry)

    return results
