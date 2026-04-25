"""
Wireless planning module.
Evaluates Okumura-Hata path loss at sample distances,
computes received power, and generates a 2-D coverage map for heatmap display.
"""
import numpy as np

from src.propagation import okumura_hata


def evaluate_wireless(config: dict) -> list:
    """
    Return a table of {distance_km, path_loss_db, rx_power_dbm}
    at the sample distances defined in the YAML config.
    """
    freq = config["wireless"]["frequency_mhz"]
    hb = config["wireless"]["base_height_m"]
    hm = config["wireless"]["mobile_height_m"]
    distances = config["wireless"]["sample_distances_km"]

    tx_power_dbm = config["wireless"].get("tx_power_dbm", 46)
    antenna_gain_dbi = config["wireless"].get("antenna_gain_dbi", 17)
    cable_loss_db = config["wireless"].get("cable_loss_db", 2)
    rx_gain_dbi = config["wireless"].get("rx_antenna_gain_dbi", 0)
    eirp_dbm = tx_power_dbm + antenna_gain_dbi - cable_loss_db

    results = []
    for d in distances:
        loss = okumura_hata(freq, hb, hm, d)
        rx_power = eirp_dbm - loss + rx_gain_dbi
        results.append(
            {
                "distance_km": d,
                "path_loss_db": round(loss, 2),
                "rx_power_dbm": round(rx_power, 2),
            }
        )
    return results


def _coverage_radius_km(
    eirp_dbm: float,
    rx_gain_dbi: float,
    threshold_dbm: float,
    freq: float,
    hb: float,
    hm: float,
    d_min: float = 0.1,
    d_max: float = 50.0,
    tol: float = 0.01,
) -> float:
    """
    Binary-search for the distance (km) at which Rx power equals threshold_dbm.
    Returns d_max if coverage never falls to the threshold within that range.
    """
    def rx_at(d):
        return eirp_dbm - okumura_hata(freq, hb, hm, d) + rx_gain_dbi

    if rx_at(d_max) > threshold_dbm:
        return d_max  # still above threshold at max search range

    lo, hi = d_min, d_max
    while (hi - lo) > tol:
        mid = (lo + hi) / 2
        if rx_at(mid) > threshold_dbm:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 2)


def compute_coverage_map(
    config: dict,
    grid_points: int = 80,
    max_range_km: float = None,
) -> dict:
    """
    Generate a 2-D grid of received signal power (dBm) centred on the
    base station.  Uses Okumura-Hata path loss with the YAML wireless
    parameters.  Minimum distance clamped at 0.1 km to avoid log(0).

    max_range_km is computed automatically when not supplied:
    it is set to the coverage radius (where Rx power = edge threshold)
    plus 25% margin, so the threshold contour is always fully visible.

    Returns x_km, y_km coordinate arrays, rx_power_dbm 2-D grid,
    and two coverage threshold values.
    """
    freq = config["wireless"]["frequency_mhz"]
    hb = config["wireless"]["base_height_m"]
    hm = config["wireless"]["mobile_height_m"]

    tx_power_dbm   = config["wireless"].get("tx_power_dbm", 46)
    antenna_gain   = config["wireless"].get("antenna_gain_dbi", 17)
    cable_loss     = config["wireless"].get("cable_loss_db", 2)
    rx_gain_dbi    = config["wireless"].get("rx_antenna_gain_dbi", 0)
    rx_sensitivity = config["wireless"].get("rx_sensitivity_dbm", -95)
    eirp_dbm       = tx_power_dbm + antenna_gain - cable_loss

    threshold_1 = rx_sensitivity        # edge threshold  e.g. -95 dBm
    threshold_2 = rx_sensitivity + 5    # quality threshold e.g. -90 dBm

    # Auto-size the map so the edge-threshold contour is fully visible
    if max_range_km is None:
        r_edge = _coverage_radius_km(
            eirp_dbm, rx_gain_dbi, threshold_1, freq, hb, hm
        )
        max_range_km = round(r_edge * 1.25, 1)   # 25 % padding beyond the edge
        max_range_km = max(max_range_km, 2.0)     # never smaller than 2 km

    xs = np.linspace(-max_range_km, max_range_km, grid_points)
    ys = np.linspace(-max_range_km, max_range_km, grid_points)

    rx_power = np.zeros((grid_points, grid_points))
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            d = float(np.sqrt(x ** 2 + y ** 2))
            d = max(d, 0.1)
            pl = okumura_hata(freq, hb, hm, d)
            rx_power[i, j] = eirp_dbm - pl + rx_gain_dbi

    return {
        "x_km": xs.tolist(),
        "y_km": ys.tolist(),
        "rx_power_dbm": rx_power.tolist(),
        "threshold_1_dbm": threshold_1,
        "threshold_2_dbm": threshold_2,
        "max_range_km": max_range_km,
    }
