# TELE 527 Python-Based Network Planning PBL Project — Group 02

## Domain
Private industrial LTE network planning and performance evaluation.

## End-to-end pipeline
Scenario configuration → Topology modelling → Traffic generation → Routing → Wireless coverage analysis → Backhaul evaluation → QoS assessment → Teletraffic dimensioning → Signaling & setup delay → Forecasting → Stress testing → Dashboard visualisation

## Datasets used
All data is generated through simulation based on the scenario configuration file:
- `configs/scenario_group2.yaml` — defines network topology, traffic classes, wireless parameters, backhaul link budgets, failure settings, forecasting parameters, and KPI targets

## Student role allocation
| Student | Role | Key responsibility |
|---|---|---|
| Goutham | System architect | Full pipeline integration, repository structure, orchestration, report coordination |
| Wadza | Signal processing & wireless lead | Propagation modelling, Okumura-Hata path loss, coverage analysis |
| Audrey | Routing & topology lead | NetworkX graph construction, Dijkstra shortest-path routing, failure injection |
| Tinawo | Traffic & QoS lead | Traffic class modelling, QoS metric computation, KPI compliance evaluation |
| Simangaliso | Forecasting & stress testing lead | Compound growth forecasting, breaking-point study, sensitivity analysis |

## Repository layout
```
tele527-group2-private-lte/
├── .gitignore
├── .streamlit/
│   └── config.toml          Streamlit dark theme configuration
├── requirements.txt
├── run_dashboard.py         Dashboard entry point
├── main.py                  Headless pipeline entry point
├── configs/
│   └── scenario_group2.yaml Scenario configuration
├── src/
│   ├── __init__.py
│   ├── config_loader.py
│   ├── topology.py
│   ├── traffic.py
│   ├── routing.py
│   ├── propagation.py       Okumura-Hata path loss model
│   ├── wireless.py          Coverage map with auto-ranging
│   ├── backhaul.py          Microwave link budget
│   ├── qos.py
│   ├── teletraffic.py       Erlang B dimensioning
│   ├── signaling.py         M/D/1 call setup delay model
│   ├── forecasting.py
│   ├── stress_test.py
│   ├── dashboard.py
│   └── plotting.py
├── tests/
│   ├── __init__.py
│   ├── test_topology.py
│   ├── test_traffic.py
│   └── test_qos.py
└── outputs/
    └── figures/             Generated stress test figures
```

## Setup and run

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the full headless simulation pipeline:
```bash
python main.py
```

Launch the interactive dashboard:
```bash
python -m streamlit run run_dashboard.py
```

Run the test suite:
```bash
python -m pytest tests/ -v
```

## Dashboard tabs and interactivity

The Streamlit dashboard has 8 tabs:

| Tab | Contents |
|---|---|
|  Network Overview | Topology diagram, routing table, traffic classes, network links |
|  QoS Performance | KPI cards (delay, jitter, throughput, packet loss, blocking), KPI compliance table |
|  Coverage & Power | Path loss table, path loss chart, 2-D Okumura-Hata coverage heatmap |
|  Microwave Backhaul | Full link budget table (EIRP, FSPL, RSL, margins), capacity bar chart, failure state |
|  Teletraffic & Erlang B | Blocking probability, Erlang B dimensioning curve, traffic class summary |
|  Signaling & Setup Delay | Per-BS setup delay table, M/D/1 burst sweep charts |
|  Forecasting | Traffic growth table, current vs forecast bar chart, upgrade trigger alerts |
|  Stress & Failure | Baseline vs failure comparison table and bar charts, breaking-point trend charts |

### Sidebar controls

| Control | Effect |
|---|---|
| Offered Load Multiplier (0.5–3.0) | Scales all traffic classes; drives stress test and Erlang B |
| Random Seed | Fixes simulation for reproducible runs |
| Carrier Frequency (MHz) | Changes Okumura-Hata path loss and auto-resizes coverage map |
| Base Station Antenna Height (m) | Changes path loss and coverage radius in real time |
| Reuse Factor | Updates frequency reuse planning metric |
| Sector Count | Updates sectorization metric |
| Voice Channels (N) | Changes Erlang B blocking directly |
| Forecast Horizon (years) | Changes forecast window |
| Annual Traffic Growth Rate (%) | Changes compound growth projection |
| Enable Backhaul Failure | Injects CORE1–CORE2 link failure; shows rerouting and QoS impact |
| Failed Link From / To | Selects which link to remove |

## Scenario configuration
Key parameters defined in `configs/scenario_group2.yaml`:

| Parameter | Value |
|---|---|
| Base stations | 5 (BS1–BS5) |
| Core nodes | 2 (CORE1, CORE2) |
| Access link capacity | 100 Mbps per link |
| Inter-core link capacity | 500 Mbps |
| Total baseline offered load | 200 Mbps |
| Wireless frequency | 1800 MHz (adjustable via sidebar) |
| Base station antenna height | 30 m (adjustable via sidebar) |
| Propagation model | Okumura-Hata |
| Voice channels | 15 (adjustable via sidebar) |
| Voice offered traffic | 8.0 Erlang |
| Microwave backhaul frequency | 7.5 GHz (BS links), 11 GHz (core link) |
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
| Maximum voice blocking (Erlang B) | ≤ 2.0% |

## Outputs
After running `main.py`, the project writes:
- Stress test figures for delay, packet loss, throughput, and site availability (baseline and failure scenarios) to `outputs/figures/`
- QoS metrics, routing tables, backhaul status, and forecast results printed to console

All results are also accessible interactively through the Streamlit dashboard.

## Notes
The project is intentionally modular so each student can present a clear technical contribution while still producing one integrated end-to-end system. All scenario assumptions are fully controlled through `configs/scenario_group2.yaml`, allowing experiments to be repeated without modifying source code. The coverage map auto-scales its range based on the computed coverage radius so threshold contours are always fully visible regardless of frequency or antenna height.
