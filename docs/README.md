# TELE 527 Python-Based Network Planning PBL Project - Group 02

## Domain
Private industrial LTE network planning and performance evaluation.

## End-to-end pipeline
Scenario configuration → Topology modelling → Traffic generation → Routing → Wireless coverage analysis → Backhaul evaluation → QoS assessment → Forecasting → Stress testing → Dashboard visualisation

## Datasets used
All data is generated through simulation based on the scenario configuration file:
- `configs/scenario_group2.yaml` — defines network topology, traffic classes, wireless parameters, failure settings, forecasting parameters, and KPI targets

## Student role allocation
- **Goutham — System architect:** full pipeline integration, repository structure, orchestration, report coordination
- **Wadza — Signal processing & wireless lead:** propagation modelling, Okumura-Hata path loss, coverage analysis
- **Audrey — Routing & topology lead:** NetworkX graph construction, Dijkstra shortest-path routing, failure injection
- **Tinawo — Traffic & QoS lead:** traffic class modelling, QoS metric computation, KPI compliance evaluation
- **Karabo — Forecasting & stress testing lead:** compound growth forecasting, breaking-point study, sensitivity analysis
- **Simangaliso — Dashboard & backhaul lead:** Streamlit dashboard, backhaul evaluation, visualisation outputs

## Repository layout
```
tele527-group2-private-lte/
  configs/            scenario YAML configuration
  src/                implementation modules
    config_loader.py
    topology.py
    traffic.py
    routing.py
    wireless.py
    propagation.py
    backhaul.py
    qos.py
    forecasting.py
    stress_test.py
    dashboard.py
    plotting.py
    signaling.py
  outputs/
    figures/          generated stress test and coverage figures
  tests/              unit and integration checks
  run_dashboard.py    dashboard entry point
  requirements.txt
```

## Run

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the full simulation pipeline:
```bash
python src/main.py
```

Launch the interactive dashboard:
```bash
streamlit run run_dashboard.py
```

## Outputs
After running, the project writes:
- Stress test figures for delay, packet loss, throughput, and site availability (baseline and failure scenarios) to `outputs/figures/`
- QoS metrics, routing tables, backhaul status, and forecast results printed to console
- All results accessible interactively through the Streamlit dashboard

## Scenario configuration
Key parameters defined in `configs/scenario_group2.yaml`:

| Parameter | Value |
|---|---|
| Base stations | 5 (BS1–BS5) |
| Core nodes | 2 (CORE1, CORE2) |
| Access link capacity | 100 Mbps |
| Inter-core link capacity | 500 Mbps |
| Total baseline offered load | 200 Mbps |
| Wireless frequency | 1800 MHz |
| Propagation model | Okumura-Hata |
| Annual traffic growth rate | 15% |
| Forecast horizon | 3 years |
| Failure scenario | CORE1–CORE2 link removal |

## KPI targets

| KPI | Target |
|---|---|
| Maximum average delay | ≤ 80 ms |
| Maximum packet loss | ≤ 2.5% |
| Minimum throughput | ≥ 180 Mbps |
| Minimum site availability | ≥ 80% |

## Notes
The project is intentionally modular so each student can present a clear technical contribution while still producing one integrated end-to-end system. Scenario assumptions are fully controlled through the YAML configuration file, allowing experiments to be repeated without modifying source code.

