def forecast_traffic(traffic, config: dict):
    growth_rate = config["forecasting"]["annual_growth_rate"]
    years = config["forecasting"]["years"]

    results = []
    for item in traffic:
        current = item["offered_load"]
        future = current * ((1 + growth_rate) ** years)
        results.append({
            "class": item["class"],
            "current_load": current,
            "forecast_load": round(future, 2)
        })

    return results