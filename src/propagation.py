import math


def okumura_hata(f_mhz: float, hb_m: float, hm_m: float, d_km: float) -> float:
    a_hm = (1.1 * math.log10(f_mhz) - 0.7) * hm_m - (1.56 * math.log10(f_mhz) - 0.8)
    loss = (
        69.55
        + 26.16 * math.log10(f_mhz)
        - 13.82 * math.log10(hb_m)
        - a_hm
        + (44.9 - 6.55 * math.log10(hb_m)) * math.log10(d_km)
    )
    return loss