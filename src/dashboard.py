import pandas as pd
import streamlit as st

from src.config_loader import load_config
from src.topology import build_topology, apply_failure
from src.traffic import generate_traffic
from src.routing import compute_routes
from src.wireless import evaluate_wireless
from src.backhaul import evaluate_backhaul
from src.qos import evaluate_qos
from src.forecasting import forecast_traffic
from src.stress_test import run_breaking_point_study


def render_custom_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            color: #e2e8f0;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1.5rem;
            max-width: 1400px;
        }

        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
            font-weight: 800 !important;
            opacity: 1 !important;
        }

        p, div, span, label {
            color: #e2e8f0;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: #1e293b;
            border-radius: 10px;
            padding: 10px 18px;
            color: #e2e8f0;
        }

        .stTabs [aria-selected="true"] {
            background-color: #2563eb !important;
            color: white !important;
        }

        .metric-card {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.25);
            margin-bottom: 12px;
        }

        .metric-title {
            font-size: 0.95rem;
            color: #94a3b8;
            margin-bottom: 6px;
        }

        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #f8fafc;
        }

        .section-card {
            background-color: #111827;
            border: 1px solid #334155;
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 18px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.22);
        }

        .small-note {
            color: #cbd5e1 !important;
            font-size: 0.92rem;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid #334155;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a, #111827);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(title: str, value: str | int | float) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_start(title: str, subtitle: str | None = None) -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader(title)
    if subtitle:
        st.markdown(
            f'<div class="small-note">{subtitle}</div>',
            unsafe_allow_html=True,
        )


def section_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def build_route_dataframe(routes: dict) -> pd.DataFrame:
    rows = []
    for site, details in routes.items():
        path = details.get("path")
        rows.append(
            {
                "Base Station": site,
                "Reachable": details.get("reachable", False),
                "Path": " -> ".join(path) if path else "No path",
                "Path Delay (ms)": details.get("path_delay_ms"),
            }
        )
    return pd.DataFrame(rows)


def build_kpi_dataframe(qos_results: dict, kpi_targets: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "KPI": "Critical Delay",
                "Measured": qos_results["average_delay_ms"],
                "Target": f"<= {kpi_targets['max_delay_ms_critical']}",
                "Status": (
                    "PASS"
                    if qos_results["average_delay_ms"] <= kpi_targets["max_delay_ms_critical"]
                    else "FAIL"
                ),
            },
            {
                "KPI": "Packet Loss",
                "Measured": qos_results["packet_loss_percent"],
                "Target": f"<= {kpi_targets['max_packet_loss_percent']}",
                "Status": (
                    "PASS"
                    if qos_results["packet_loss_percent"] <= kpi_targets["max_packet_loss_percent"]
                    else "FAIL"
                ),
            },
            {
                "KPI": "Throughput",
                "Measured": qos_results["throughput_mbps"],
                "Target": f">= {kpi_targets['min_throughput_mbps']}",
                "Status": (
                    "PASS"
                    if qos_results["throughput_mbps"] >= kpi_targets["min_throughput_mbps"]
                    else "FAIL"
                ),
            },
            {
                "KPI": "Site Availability",
                "Measured": qos_results["site_availability_percent"],
                "Target": f">= {kpi_targets['min_site_availability_percent']}",
                "Status": (
                    "PASS"
                    if qos_results["site_availability_percent"] >= kpi_targets["min_site_availability_percent"]
                    else "FAIL"
                ),
            },
        ]
    )


def build_stress_dataframe(stress_results: dict) -> pd.DataFrame:
    history = stress_results.get("history", [])
    rows = []

    for entry in history:
        qos = entry.get("qos_results", {})
        failures = entry.get("failures", [])
        rows.append(
            {
                "Load Multiplier": entry.get("load_multiplier"),
                "Delay (ms)": qos.get("average_delay_ms"),
                "Jitter (ms)": qos.get("average_jitter_ms"),
                "Throughput (Mbps)": qos.get("throughput_mbps"),
                "Packet Loss (%)": qos.get("packet_loss_percent"),
                "Availability (%)": qos.get("site_availability_percent"),
                "Failures": ", ".join(failures) if failures else "None",
            }
        )

    return pd.DataFrame(rows)


def run_dashboard() -> None:
    st.set_page_config(
        page_title="TELE527 Group 2 Dashboard",
        page_icon="📡",
        layout="wide",
    )

    render_custom_css()

    config: dict = load_config("configs/scenario_group2.yaml")
    if not config:
        st.error("Configuration could not be loaded.")
        st.stop()

    failure_cfg: dict = config.get("failure") or {}
    failed_link_cfg: dict = failure_cfg.get("failed_link") or {}
    wireless_cfg: dict = config.get("wireless") or {}
    network_cfg: dict = config.get("network") or {}
    kpi_targets: dict = config.get("kpi_targets") or {}

    st.markdown(
        """
        <h1 style="font-weight:900; font-size:2.5rem; color:#ffffff; margin-bottom:0.2rem;">
             Private Industrial LTE Network Planning Dashboard
        </h1>
        <h3 style="font-weight:700; color:#cbd5e1; margin-top:0;">
            Group 2 — TELE527 Python-Based PBL Laboratory Programme
        </h3>
        <p style="color:#cbd5e1; margin-bottom:1.2rem;">
            Interactive dashboard for topology, QoS, wireless planning, backhaul resilience, forecasting, and stress testing.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("## ⚙️ Scenario Controls")

    load_multiplier = st.sidebar.slider(
        "Offered Load Multiplier",
        min_value=0.5,
        max_value=3.0,
        value=float(config.get("load_multiplier", 1.0)),
        step=0.25,
    )

    failure_enabled = st.sidebar.checkbox(
        "Enable Backhaul Failure",
        value=bool(failure_cfg.get("enabled", False)),
    )

    reuse_factor = st.sidebar.selectbox(
        "Reuse Factor",
        options=[1, 3, 4, 7],
        index=1,
    )

    sector_count = st.sidebar.selectbox(
        "Sector Count",
        options=[1, 3],
        index=1,
    )

    failed_link_from = st.sidebar.text_input(
        "Failed Link From",
        value=str(failed_link_cfg.get("from", "CORE1")),
    )

    failed_link_to = st.sidebar.text_input(
        "Failed Link To",
        value=str(failed_link_cfg.get("to", "CORE2")),
    )

    config["load_multiplier"] = load_multiplier
    config["failure"]["enabled"] = failure_enabled
    config["failure"]["failed_link"]["from"] = failed_link_from
    config["failure"]["failed_link"]["to"] = failed_link_to
    config["wireless"]["reuse_factor"] = reuse_factor
    config["wireless"]["sector_count"] = sector_count

    topology = build_topology(config)
    topology, failed_info = apply_failure(topology, config)

    traffic = generate_traffic(config)
    routes = compute_routes(topology, traffic, config)
    wireless_results = evaluate_wireless(config)
    backhaul_results = evaluate_backhaul(topology, config, failed_info)
    qos_results = evaluate_qos(
        traffic,
        routes,
        wireless_results,
        backhaul_results,
        config,
        failed_info,
    )
    forecast_results = forecast_traffic(traffic, config)
    stress_results = run_breaking_point_study(config)

    base_stations = network_cfg.get("base_stations", [])
    core_nodes = network_cfg.get("core_nodes", [])

    st.markdown("---")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Base Stations", len(base_stations))
    with c2:
        metric_card("Core Nodes", len(core_nodes))
    with c3:
        metric_card("Load Multiplier", load_multiplier)
    with c4:
        metric_card("Failure Active", "Yes" if failed_info.get("failure_enabled") else "No")
    with c5:
        metric_card("Availability", f"{qos_results['site_availability_percent']}%")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            " Network Overview",
            " QoS Performance",
            " Coverage & Power",
            " Microwave Backhaul",
            " Forecasting",
            " Stress vs Failure",
        ]
    )

    with tab1:
        section_start("Network Overview", "Topology status, routing summary, and traffic classes.")
        col1, col2 = st.columns([1.2, 1])

        with col1:
            st.markdown("#### Routing Status")
            routes_df = build_route_dataframe(routes)
            st.dataframe(routes_df, use_container_width=True, height=260)

        with col2:
            st.markdown("#### Traffic Classes")
            traffic_df = pd.DataFrame(traffic)
            st.dataframe(traffic_df, use_container_width=True, height=260)

        st.markdown("#### Network Links")
        backhaul_df = pd.DataFrame(backhaul_results)
        st.dataframe(backhaul_df, use_container_width=True)
        section_end()

    with tab2:
        section_start("QoS Performance", "Real-time KPI monitoring against target thresholds.")

        q1, q2, q3, q4 = st.columns(4)
        with q1:
            metric_card("Average Delay (ms)", qos_results["average_delay_ms"])
        with q2:
            metric_card("Average Jitter (ms)", qos_results["average_jitter_ms"])
        with q3:
            metric_card("Throughput (Mbps)", qos_results["throughput_mbps"])
        with q4:
            metric_card("Packet Loss (%)", qos_results["packet_loss_percent"])

        q5, q6, q7 = st.columns(3)
        with q5:
            metric_card("Reachable Sites", qos_results["reachable_sites"])
        with q6:
            metric_card("Total Sites", qos_results["total_sites"])
        with q7:
            metric_card("Failure Status", "ON" if qos_results["failure_active"] else "OFF")

        st.markdown("#### KPI Compliance")
        if kpi_targets:
            kpi_df = build_kpi_dataframe(qos_results, kpi_targets)
            st.dataframe(kpi_df, use_container_width=True)
        else:
            st.warning("KPI targets are missing from the configuration file.")
        section_end()

    with tab3:
        section_start("Coverage & Received Power", "Wireless path loss behaviour over distance.")
        wireless_df = pd.DataFrame(wireless_results)
        st.dataframe(wireless_df, use_container_width=True)

        if not wireless_df.empty:
            st.markdown("#### Path Loss Trend")
            st.line_chart(
                wireless_df.set_index("distance_km")["path_loss_db"],
                height=420,
            )

        info1, info2 = st.columns(2)
        with info1:
            metric_card("Reuse Factor", wireless_cfg.get("reuse_factor", reuse_factor))
        with info2:
            metric_card("Sector Count", wireless_cfg.get("sector_count", sector_count))

        st.info(
            "Higher distance leads to larger path loss. Reuse factor and sectorization affect interference, capacity, and cell planning tradeoffs."
        )
        section_end()

    with tab4:
        section_start("Microwave Backhaul", "Backhaul capacity and failure-state visibility.")
        backhaul_df = pd.DataFrame(backhaul_results)
        st.dataframe(backhaul_df, use_container_width=True)

        if not backhaul_df.empty and "capacity_mbps" in backhaul_df.columns:
            chart_df = backhaul_df.copy().set_index("link")
            st.markdown("#### Link Capacity")
            st.bar_chart(chart_df["capacity_mbps"], height=420)

        st.markdown("#### Failure Information")
        st.json(failed_info)
        section_end()

    with tab5:
        section_start("Forecasting", "Traffic growth outlook and upgrade recommendation.")
        forecast_df = pd.DataFrame(forecast_results)
        st.dataframe(forecast_df, use_container_width=True)

        if not forecast_df.empty:
            chart_df = forecast_df.set_index("class")[["current_load", "forecast_load"]]
            st.markdown("#### Current vs Forecast Load")
            st.bar_chart(chart_df, height=420)

        overloaded_classes = forecast_df[forecast_df["forecast_load"] > 100]
        if len(overloaded_classes) > 0:
            st.warning("A phased upgrade is recommended for traffic classes projected above 100 load units.")
            st.dataframe(overloaded_classes, use_container_width=True)
        else:
            st.success("No immediate forecast-based upgrade trigger detected.")
        section_end()

    with tab6:
        section_start("Stress vs Failure", "Breaking-point study and KPI degradation with load increase.")
        stress_df = build_stress_dataframe(stress_results)

        if not stress_df.empty:
            st.dataframe(stress_df, use_container_width=True)

            if "Load Multiplier" in stress_df.columns:
                st.markdown("#### Stress Trend")
                chart_df = stress_df.set_index("Load Multiplier")[
                    ["Delay (ms)", "Packet Loss (%)", "Availability (%)"]
                ]
                st.line_chart(chart_df, height=450)

        first_failure = stress_results.get("first_failure_multiplier")
        failed_kpis = stress_results.get("failed_kpis", [])

        b1, b2 = st.columns(2)
        with b1:
            metric_card(
                "First Failure Multiplier",
                first_failure if first_failure is not None else "No failure",
            )
        with b2:
            metric_card(
                "Failed KPIs",
                ", ".join(failed_kpis) if failed_kpis else "None",
            )

        if first_failure is not None:
            st.error(
                f"First KPI failure occurs at load multiplier {first_failure}. Failed KPIs: {', '.join(failed_kpis)}"
            )
        else:
            st.success("No KPI failure detected within the tested load range.")
        section_end()

    st.markdown("---")
    st.caption("TELE527 Group 2 Dashboard • Private Industrial LTE Network")