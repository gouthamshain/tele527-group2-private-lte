"""
Teletraffic engineering module.
Implements Erlang B blocking probability for voice traffic dimensioning.
"""


def erlang_b(traffic_erlangs: float, channels: int) -> float:
    """
    Compute Erlang B blocking probability using the numerically stable
    iterative formula.  Works correctly for large traffic values.

    B(A, 0) = 1
    B(A, n) = (A/n * B(A, n-1)) / (1 + A/n * B(A, n-1))

    Equivalent stable form:  inv_B starts at 1, then for n = 1..N:
        inv_B = 1 + (n / A) * inv_B
    B = 1 / inv_B
    """
    if traffic_erlangs <= 0:
        return 0.0
    if channels == 0:
        return 1.0

    inv_b = 1.0
    for n in range(1, channels + 1):
        inv_b = 1.0 + (n / traffic_erlangs) * inv_b
    return 1.0 / inv_b


def erlang_b_channels(traffic_erlangs: float, target_blocking: float) -> int:
    """
    Return the minimum number of channels needed to achieve
    blocking probability <= target_blocking (expressed as a fraction, e.g. 0.02).
    """
    if traffic_erlangs <= 0:
        return 1
    for n in range(1, 2001):
        if erlang_b(traffic_erlangs, n) <= target_blocking:
            return n
    return 2000


def erlang_b_curve(traffic_erlangs: float, n_min: int, n_max: int) -> list:
    """
    Return a list of {channels, blocking_percent} dicts spanning [n_min, n_max].
    Used to draw the Erlang B dimensioning curve in the dashboard.
    """
    return [
        {
            "channels": n,
            "blocking_percent": round(erlang_b(traffic_erlangs, n) * 100, 4),
        }
        for n in range(n_min, n_max + 1)
    ]


def compute_teletraffic(config: dict) -> dict:
    """
    Compute all teletraffic metrics for the current scenario load.
    Returns blocking probability, dimensioning recommendation, and curve data.
    """
    tt_cfg = config.get("teletraffic", {})
    load_multiplier = config.get("load_multiplier", 1.0)

    base_erlangs = tt_cfg.get("voice_erlangs", 8.0)
    voice_channels = tt_cfg.get("voice_channels", 15)
    target_pct = tt_cfg.get("target_blocking_percent", 2.0)

    # Scale offered voice traffic by current load multiplier
    voice_erlangs = base_erlangs * load_multiplier
    blocking = erlang_b(voice_erlangs, voice_channels)
    blocking_pct = round(blocking * 100, 4)
    min_channels = erlang_b_channels(voice_erlangs, target_pct / 100.0)

    # Build curve: show from (voice_channels - 8) to (min_channels + 6)
    c_min = max(1, voice_channels - 8)
    c_max = max(min_channels + 6, voice_channels + 6)
    curve = erlang_b_curve(voice_erlangs, c_min, c_max)

    # Traffic class summary (for the table in the dashboard)
    traffic_classes = config.get("traffic_classes", [])
    traffic_summary = [
        {
            "class": tc["name"],
            "offered_load_mbps": round(tc["offered_load"] * load_multiplier, 2),
            "priority": tc["priority"],
        }
        for tc in traffic_classes
    ]

    return {
        "voice_erlangs": round(voice_erlangs, 3),
        "voice_channels": voice_channels,
        "blocking_percent": blocking_pct,
        "target_blocking_percent": target_pct,
        "min_channels_for_target": min_channels,
        "status": "PASS" if blocking_pct <= target_pct else "FAIL",
        "erlang_b_curve": curve,
        "traffic_summary": traffic_summary,
    }
