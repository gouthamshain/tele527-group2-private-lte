from src.propagation import okumura_hata


def evaluate_wireless(config: dict):
    freq = config["wireless"]["frequency_mhz"]
    hb = config["wireless"]["base_height_m"]
    hm = config["wireless"]["mobile_height_m"]
    distances = config["wireless"]["sample_distances_km"]

    results = []
    for d in distances:
        loss = okumura_hata(freq, hb, hm, d)
        results.append({
            "distance_km": d,
            "path_loss_db": loss
        })

    return results