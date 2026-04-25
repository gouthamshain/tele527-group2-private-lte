"""
TELE527 Group 2 — Private Industrial LTE Network Planning Dashboard
Fully theme-adaptive: works in both Streamlit dark and light mode.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
import pandas as pd
import streamlit as st

from src.config_loader import load_config
from src.topology import build_topology, apply_failure
from src.traffic import generate_traffic
from src.routing import compute_routes
from src.wireless import evaluate_wireless, compute_coverage_map
from src.backhaul import evaluate_backhaul
from src.qos import evaluate_qos
from src.teletraffic import compute_teletraffic
from src.signaling import compute_signaling_results
from src.forecasting import forecast_traffic
from src.stress_test import run_breaking_point_study, run_scenario_comparison


# ── Theme helper ──────────────────────────────────────────────────────────────

def _mpl_colors() -> dict:
    """
    Read Streamlit's active theme and return a colour palette for matplotlib.
    Falls back to dark-mode defaults when the theme is not explicitly set.
    """
    text    = st.get_option("theme.textColor")                or "#e2e8f0"
    bg      = st.get_option("theme.backgroundColor")          or "#0f172a"
    sec_bg  = st.get_option("theme.secondaryBackgroundColor") or "#1e293b"
    primary = st.get_option("theme.primaryColor")             or "#2563eb"
    try:
        h = bg.lstrip("#")
        lum = (int(h[0:2], 16) + int(h[2:4], 16) + int(h[4:6], 16)) / 3
        is_dark = lum < 128
    except Exception:
        is_dark = True
    return {
        "text":    text,
        "bg":      bg,
        "sec_bg":  sec_bg,
        "primary": primary,
        "grid":    (148/255, 163/255, 184/255, 0.18) if is_dark else (100/255, 116/255, 139/255, 0.22),
        "is_dark": is_dark,
        "accent1": "#38bdf8"  if is_dark else "#0284c7",
        "accent2": "#f87171"  if is_dark else "#dc2626",
        "accent3": "#a78bfa"  if is_dark else "#7c3aed",
        "warning": "#fbbf24"  if is_dark else "#d97706",
    }


def _style_ax(ax, fig, c: dict,
              title: str = "", xlabel: str = "", ylabel: str = "") -> None:
    """Apply theme colours to a matplotlib Axes + Figure."""
    fig.patch.set_facecolor(c["sec_bg"])
    ax.set_facecolor(c["bg"])
    ax.tick_params(colors=c["text"])
    for sp in ax.spines.values():
        sp.set_edgecolor(c["grid"])
    ax.grid(True, color=c["grid"], linewidth=0.5)
    if title:  ax.set_title(title,  color=c["text"], fontsize=11, fontweight="bold")
    if xlabel: ax.set_xlabel(xlabel, color=c["text"])
    if ylabel: ax.set_ylabel(ylabel, color=c["text"])


# ── CSS ───────────────────────────────────────────────────────────────────────

def render_custom_css() -> None:
    """
    All colours use Streamlit CSS variables, so the design adapts
    automatically when the user switches between dark and light mode.
    No hardcoded hex colours are used for backgrounds or text.
    """
    st.markdown(
        """
        <style>
        /* Layout */
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 1.4rem;
            max-width: 1400px;
        }

        /* Headings inherit theme text colour */
        h1, h2, h3, h4, h5, h6 { font-weight: 800 !important; }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 6px; }
        .stTabs [data-baseweb="tab"] {
            background: var(--secondary-background-color);
            border-radius: 10px;
            padding: 8px 14px;
            color: var(--text-color);
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background: var(--primary-color) !important;
            color: #ffffff !important;
        }

        /* Metric card — uses theme background and text */
        .metric-card {
            background: var(--secondary-background-color);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.10);
            margin-bottom: 12px;
        }
        .metric-title {
            font-size: 0.87rem;
            color: var(--text-color);
            opacity: 0.60;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.72rem;
            font-weight: 700;
            color: var(--text-color);
        }

        /* Section card */
        .section-card {
            background: var(--secondary-background-color);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            padding: 20px;
            margin-bottom: 18px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
        }

        /* Small note text */
        .small-note {
            font-size: 0.91rem;
            color: var(--text-color);
            opacity: 0.70;
        }

        /* Data frame border */
        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.16);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── UI helpers ────────────────────────────────────────────────────────────────

def metric_card(title: str, value) -> None:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">{title}</div>'
        f'<div class="metric-value">{value}</div>'
        f'</div>',
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


# ── DataFrame builders ────────────────────────────────────────────────────────

def build_route_dataframe(routes: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Base Station": site,
                "Reachable": d.get("reachable", False),
                "Path": " -> ".join(d["path"]) if d.get("path") else "No path",
                "Path Delay (ms)": d.get("path_delay_ms"),
            }
            for site, d in routes.items()
        ]
    )


def build_kpi_dataframe(qos_results: dict, kpi_targets: dict) -> pd.DataFrame:
    rows = [
        {
            "KPI": "Critical Delay",
            "Measured": f"{qos_results['average_delay_ms']} ms",
            "Target":   f"<= {kpi_targets['max_delay_ms_critical']} ms",
            "Status": "PASS" if qos_results["average_delay_ms"] <= kpi_targets["max_delay_ms_critical"] else "FAIL",
        },
        {
            "KPI": "Packet Loss",
            "Measured": f"{qos_results['packet_loss_percent']}%",
            "Target":   f"<= {kpi_targets['max_packet_loss_percent']}%",
            "Status": "PASS" if qos_results["packet_loss_percent"] <= kpi_targets["max_packet_loss_percent"] else "FAIL",
        },
        {
            "KPI": "Throughput",
            "Measured": f"{qos_results['throughput_mbps']} Mbps",
            "Target":   f">= {kpi_targets['min_throughput_mbps']} Mbps",
            "Status": "PASS" if qos_results["throughput_mbps"] >= kpi_targets["min_throughput_mbps"] else "FAIL",
        },
        {
            "KPI": "Site Availability",
            "Measured": f"{qos_results['site_availability_percent']}%",
            "Target":   f">= {kpi_targets['min_site_availability_percent']}%",
            "Status": "PASS" if qos_results["site_availability_percent"] >= kpi_targets["min_site_availability_percent"] else "FAIL",
        },
        {
            "KPI": "Voice Blocking (Erlang B)",
            "Measured": f"{qos_results.get('voice_blocking_percent', 'N/A')}%",
            "Target":   f"<= {kpi_targets.get('max_voice_blocking_percent', 2.0)}%",
            "Status": (
                "PASS"
                if qos_results.get("voice_blocking_percent", 0)
                   <= kpi_targets.get("max_voice_blocking_percent", 2.0)
                else "FAIL"
            ),
        },
    ]
    return pd.DataFrame(rows)


def build_network_links_df(backhaul_results: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Link":           r["link"],
                "Capacity (Mbps)": r.get("capacity_mbps"),
                "Delay (ms)":      r.get("delay_ms"),
                "Status":          r.get("status"),
            }
            for r in backhaul_results
        ]
    )


def build_link_budget_df(backhaul_results: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Link":            r["link"],
                "Freq (GHz)":      r.get("frequency_ghz"),
                "Dist (km)":       r.get("distance_km"),
                "Tx Pwr (dBm)":    r.get("tx_power_dbm"),
                "EIRP (dBm)":      r.get("eirp_dbm"),
                "FSPL (dB)":       r.get("fspl_db"),
                "RSL (dBm)":       r.get("rsl_dbm"),
                "Rx Sens (dBm)":   r.get("rx_sensitivity_dbm"),
                "Avail Margin (dB)": r.get("available_margin_db"),
                "Fade Margin (dB)": r.get("fade_margin_db"),
                "Net Margin (dB)": r.get("net_margin_db"),
                "Budget":          r.get("budget_status", "N/A"),
            }
            for r in backhaul_results
            if "eirp_dbm" in r
        ]
    )


def build_stress_dataframe(stress_results: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Load Mult.":       e["load_multiplier"],
                "Delay (ms)":       e["qos_results"].get("average_delay_ms"),
                "Jitter (ms)":      e["qos_results"].get("average_jitter_ms"),
                "Throughput (Mbps)": e["qos_results"].get("throughput_mbps"),
                "Packet Loss (%)":  e["qos_results"].get("packet_loss_percent"),
                "Blocking (%)":     e["qos_results"].get("voice_blocking_percent"),
                "Availability (%)": e["qos_results"].get("site_availability_percent"),
                "Failures":         ", ".join(e["failures"]) if e["failures"] else "None",
            }
            for e in stress_results.get("history", [])
        ]
    )


# ── Main dashboard ────────────────────────────────────────────────────────────

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

    failure_cfg     = config.get("failure")    or {}
    failed_link_cfg = failure_cfg.get("failed_link") or {}
    wireless_cfg    = config.get("wireless")   or {}
    network_cfg     = config.get("network")    or {}
    kpi_targets     = config.get("kpi_targets") or {}

    # ── Header — no inline colours; Streamlit theme colours apply ─────────────
    st.markdown(
        """
        <h1 style="font-weight:900;font-size:2.4rem;margin-bottom:.25rem;">
        📡 Private Industrial LTE Network Planning Dashboard
        </h1>
        <h3 style="font-weight:600;margin-top:0;opacity:.8;">
        Group 2 — TELE527 Python-Based PBL · BIUST
        </h3>
        <p style="opacity:.72;margin-bottom:1rem;">
        Topology · QoS · Teletraffic · Coverage · Backhaul · Signaling · Forecasting · Stress
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    st.sidebar.markdown("## ⚙️ Scenario Controls")

    # Traffic & load
    st.sidebar.markdown("### 📶 Traffic")
    load_multiplier = st.sidebar.slider(
        "Offered Load Multiplier",
        min_value=0.5, max_value=3.0,
        value=float(config.get("load_multiplier", 1.0)), step=0.25,
    )
    random_seed = st.sidebar.number_input(
        "Random Seed",
        min_value=0, max_value=9999,
        value=int(config.get("random_seed", 42)), step=1,
        help="Fix this value for reproducible simulation runs.",
    )

    # Wireless
    st.sidebar.markdown("### 📡 Wireless")
    _freq_options = [700, 850, 900, 1800, 2100, 2600]
    _freq_default = int(config["wireless"].get("frequency_mhz", 1800))
    _freq_idx = _freq_options.index(_freq_default) if _freq_default in _freq_options else 3
    frequency_mhz = st.sidebar.selectbox(
        "Carrier Frequency (MHz)", options=_freq_options, index=_freq_idx,
        help="Changes path loss model and coverage map in real time.",
    )
    reuse_factor = st.sidebar.selectbox("Reuse Factor", [1, 3, 4, 7], index=1)
    sector_count = st.sidebar.selectbox("Sector Count", [1, 3], index=1)
    base_height_m = st.sidebar.slider(
        "BS Antenna Height (m)",
        min_value=10, max_value=100,
        value=int(config["wireless"].get("base_height_m", 30)),
        step=5,
        help="Increasing antenna height reduces path loss and extends cell coverage radius.",
    )
    mobile_height_m = st.sidebar.slider(
        "UE Height (m)",
        min_value=1, max_value=10,
        value=int(config["wireless"].get("mobile_height_m", 1)),
        step=1,
        help="Height of the mobile terminal above ground. Typically 1–2 m.",
    )

    # Teletraffic
    st.sidebar.markdown("### ☎️ Teletraffic")
    voice_channels = st.sidebar.slider(
        "Voice Channels (N)",
        min_value=5, max_value=50,
        value=int(config.get("teletraffic", {}).get("voice_channels", 15)),
        step=1,
        help="Number of voice circuits provisioned. Affects Erlang B blocking directly.",
    )

    # Forecasting
    st.sidebar.markdown("### 📈 Forecasting")
    forecast_years = st.sidebar.slider(
        "Forecast Horizon (years)",
        min_value=1, max_value=10,
        value=int(config.get("forecasting", {}).get("years", 3)),
        step=1,
    )
    growth_rate_pct = st.sidebar.slider(
        "Annual Traffic Growth Rate (%)",
        min_value=1, max_value=50,
        value=int(config.get("forecasting", {}).get("annual_growth_rate", 0.15) * 100),
        step=1,
        help="Compound annual growth rate applied to all traffic classes.",
    )

    # Failure
    st.sidebar.markdown("### ⚠️ Failure")
    failure_enabled = st.sidebar.checkbox(
        "Enable Backhaul Failure",
        value=bool(failure_cfg.get("enabled", False)),
    )
    failed_link_from = st.sidebar.text_input(
        "Failed Link From", value=str(failed_link_cfg.get("from", "CORE1"))
    )
    failed_link_to = st.sidebar.text_input(
        "Failed Link To", value=str(failed_link_cfg.get("to", "CORE2"))
    )

    # ── Apply all sidebar values to config ────────────────────────────────────
    config["load_multiplier"]                   = load_multiplier
    config["random_seed"]                       = random_seed
    config["wireless"]["frequency_mhz"]         = frequency_mhz
    config["wireless"]["reuse_factor"]          = reuse_factor
    config["wireless"]["sector_count"]          = sector_count
    config["wireless"]["base_height_m"]         = base_height_m
    config["wireless"]["mobile_height_m"]       = float(mobile_height_m)
    config["teletraffic"]["voice_channels"]     = voice_channels
    config["forecasting"]["years"]              = forecast_years
    config["forecasting"]["annual_growth_rate"] = growth_rate_pct / 100.0
    config["failure"]["enabled"]                = failure_enabled
    config["failure"]["failed_link"]["from"]    = failed_link_from
    config["failure"]["failed_link"]["to"]      = failed_link_to

    # ── Pipeline ──────────────────────────────────────────────────────────────
    topology = build_topology(config)
    topology, failed_info = apply_failure(topology, config)
    traffic = generate_traffic(config)
    routes = compute_routes(topology, traffic, config)
    wireless_results = evaluate_wireless(config)
    backhaul_results = evaluate_backhaul(topology, config, failed_info)
    qos_results = evaluate_qos(
        traffic, routes, wireless_results, backhaul_results, config, failed_info
    )
    teletraffic_results = compute_teletraffic(config)
    signaling_results = compute_signaling_results(topology, routes, traffic, config)
    forecast_results = forecast_traffic(traffic, config)
    comparison_results = run_scenario_comparison(config)
    stress_results = run_breaking_point_study(config)

    # ── Summary strip ─────────────────────────────────────────────────────────
    st.markdown("---")
    for col, (title, val) in zip(st.columns(6), [
        ("Base Stations",  len(network_cfg.get("base_stations", []))),
        ("Core Nodes",     len(network_cfg.get("core_nodes", []))),
        ("Load Multiplier", load_multiplier),
        ("Failure Active", "Yes" if failed_info.get("failure_enabled") else "No"),
        ("Availability",   f"{qos_results['site_availability_percent']}%"),
        ("Voice Blocking", f"{qos_results.get('voice_blocking_percent','N/A')}%"),
    ]):
        with col: metric_card(title, val)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "🌐 Network Overview",
        "📊 QoS Performance",
        "📶 Coverage & Power",
        "🔗 Microwave Backhaul",
        "☎️ Teletraffic & Erlang B",
        "⏱️ Signaling & Setup Delay",
        "📈 Forecasting",
        "⚠️ Stress & Failure",
    ])

    # ── 1. Network Overview ───────────────────────────────────────────────────
    with tabs[0]:
        section_start("Network Overview",
                       "Topology status, routing table, and traffic classes.")

        # ── Topology diagram ──────────────────────────────────────────────────
        st.markdown("#### Network Topology")
        import networkx as nx
        c = _mpl_colors()

        # Fixed positions: BS1-BS3 fan left of CORE1, BS4-BS5 fan right of CORE2
        _pos = {
            "BS1":   (-3.5,  1.4),
            "BS2":   (-3.5,  0.0),
            "BS3":   (-3.5, -1.4),
            "CORE1": (-1.2,  0.0),
            "CORE2": ( 1.2,  0.0),
            "BS4":   ( 3.5,  0.7),
            "BS5":   ( 3.5, -0.7),
        }

        # Identify failed link for red highlight
        _failed_edge = None
        if failed_info.get("failure_enabled"):
            _fl = failed_info.get("failed_link")
            if _fl:
                _failed_edge = tuple(_fl)

        fig_topo, ax_topo = plt.subplots(figsize=(9, 3.8))
        fig_topo.patch.set_facecolor(c["sec_bg"])
        ax_topo.set_facecolor(c["bg"])

        # Node colours by type
        _bs_nodes   = [n for n in topology.nodes() if "BS" in n]
        _core_nodes = [n for n in topology.nodes() if "CORE" in n]
        # Also account for nodes that were removed from graph due to failure
        _all_bs    = [bs["id"] for bs in network_cfg.get("base_stations", [])]
        _all_cores = [c_n["id"] for c_n in network_cfg.get("core_nodes", [])]

        # Draw on a complete reference graph (not the possibly-mutated topology)
        _ref_graph = nx.Graph()
        for lnk in network_cfg.get("links", []):
            _ref_graph.add_edge(lnk["from"], lnk["to"],
                                capacity_mbps=lnk["capacity_mbps"],
                                delay_ms=lnk["delay_ms"])

        _edge_colors, _edge_widths, _edge_styles = [], [], []
        for u, v in _ref_graph.edges():
            is_fail = (_failed_edge is not None and
                       ({u, v} == set(_failed_edge)))
            _edge_colors.append("#f87171" if is_fail else c["accent1"])
            _edge_widths.append(1.5 if is_fail else 2.5)
            _edge_styles.append("dashed" if is_fail else "solid")

        # Draw edges individually to support per-edge style
        for (u, v), ec, ew, es in zip(_ref_graph.edges(),
                                       _edge_colors, _edge_widths, _edge_styles):
            nx.draw_networkx_edges(
                _ref_graph, _pos, edgelist=[(u, v)],
                edge_color=[ec], width=ew,
                style=es, ax=ax_topo, alpha=0.85,
            )

        # Edge labels: capacity / delay
        _elabels = {
            (u, v): f"{d['capacity_mbps']} Mbps\n{d['delay_ms']} ms"
            for u, v, d in _ref_graph.edges(data=True)
        }
        nx.draw_networkx_edge_labels(
            _ref_graph, _pos, edge_labels=_elabels,
            font_size=6.5, font_color=c["text"],
            bbox=dict(boxstyle="round,pad=0.15", fc=c["sec_bg"], alpha=0.7),
            ax=ax_topo,
        )

        nx.draw_networkx_nodes(
            _ref_graph, _pos, nodelist=_all_bs,
            node_color=c["accent1"], node_size=700,
            node_shape="o", ax=ax_topo,
        )
        nx.draw_networkx_nodes(
            _ref_graph, _pos, nodelist=_all_cores,
            node_color=c["accent3"], node_size=900,
            node_shape="s", ax=ax_topo,
        )
        nx.draw_networkx_labels(
            _ref_graph, _pos, font_size=8,
            font_color="#0f172a", font_weight="bold", ax=ax_topo,
        )

        # Legend
        from matplotlib.patches import Patch
        _legend_handles = [
            Patch(color=c["accent1"], label="Base Station"),
            Patch(color=c["accent3"], label="Core Node"),
        ]
        if _failed_edge:
            _legend_handles.append(
                mlines.Line2D([], [], color="#f87171", linestyle="--",
                              linewidth=2, label=f"Failed: {_failed_edge[0]}–{_failed_edge[1]}")
            )
        ax_topo.legend(handles=_legend_handles,
                       facecolor=c["sec_bg"], labelcolor=c["text"],
                       fontsize=8, loc="upper right")
        ax_topo.set_title("Network Topology — link labels: capacity / propagation delay",
                          color=c["text"], fontsize=10, fontweight="bold")
        ax_topo.axis("off")
        fig_topo.tight_layout()
        st.pyplot(fig_topo)
        plt.close(fig_topo)

        # ── Tables ────────────────────────────────────────────────────────────
        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.markdown("#### Routing Status")
            st.dataframe(build_route_dataframe(routes),
                         use_container_width=True, height=240)
        with c2:
            st.markdown("#### Traffic Classes")
            st.dataframe(pd.DataFrame(traffic),
                         use_container_width=True, height=240)
        st.markdown("#### Network Links")
        st.dataframe(build_network_links_df(backhaul_results),
                     use_container_width=True)
        section_end()

    # ── 2. QoS Performance ────────────────────────────────────────────────────
    with tabs[1]:
        section_start("QoS Performance",
                       "Real-time KPI monitoring against target thresholds.")
        for col, (title, val) in zip(st.columns(5), [
            ("Avg Delay (ms)",    qos_results["average_delay_ms"]),
            ("Avg Jitter (ms)",   qos_results["average_jitter_ms"]),
            ("Throughput (Mbps)", qos_results["throughput_mbps"]),
            ("Packet Loss (%)",   qos_results["packet_loss_percent"]),
            ("Voice Blocking (%)",qos_results.get("voice_blocking_percent","N/A")),
        ]):
            with col: metric_card(title, val)
        for col, (title, val) in zip(st.columns(3), [
            ("Reachable Sites", qos_results["reachable_sites"]),
            ("Total Sites",     qos_results["total_sites"]),
            ("Failure Status",  "ON" if qos_results["failure_active"] else "OFF"),
        ]):
            with col: metric_card(title, val)
        st.markdown("#### KPI Compliance")
        if kpi_targets:
            st.dataframe(build_kpi_dataframe(qos_results, kpi_targets),
                         use_container_width=True)
        else:
            st.warning("KPI targets missing from configuration file.")

        with st.expander("📐 Where do these delay numbers come from?", expanded=False):
            # Recompute the terms so the explanation matches the live values
            _total_load = sum(item["offered_load"] for item in traffic)
            _reachable  = qos_results["reachable_sites"]
            _total      = qos_results["total_sites"]
            _avg_prop   = (
                sum(r["path_delay_ms"] for r in routes.values()
                    if r["reachable"] and r["path_delay_ms"] is not None)
                / max(_reachable, 1)
            )
            _fail_pen   = 15 if failed_info and failed_info.get("failure_enabled") else 0
            _unreach_pen = (_total - _reachable) * 20

            st.markdown(f"""
**Average Delay is built from four additive terms inside `qos.py`:**

| Term | Formula | Current value |
|---|---|---|
| Base processing | fixed 10 ms per packet | **10 ms** |
| Load-dependent queuing | `total_offered_load × 0.3` | **{_total_load:.1f} × 0.3 = {_total_load*0.3:.1f} ms** |
| Average propagation | mean shortest-path delay across all reachable BS routes | **{_avg_prop:.2f} ms** |
| Failure penalty | +15 ms when a backhaul link is failed | **{_fail_pen} ms** |
| Unreachable penalty | `(total_sites − reachable) × 20 ms` | **({_total} − {_reachable}) × 20 = {_unreach_pen} ms** |
| **Total** | sum of all terms | **{qos_results['average_delay_ms']} ms** |

**Propagation delays come directly from the YAML config** (`network.links[].delay_ms`):

| Link | Delay |
|---|---|
| BS1 → CORE1 | 5 ms |
| BS2 → CORE1 | 6 ms |
| BS3 → CORE1 | 4 ms |
| BS4 → CORE2 | 7 ms |
| BS5 → CORE2 | 5 ms |
| CORE1 → CORE2 | 2 ms |

BS4 and BS5 route through CORE2 → CORE1 (two hops), so their path delay is
7 + 2 = 9 ms and 5 + 2 = 7 ms respectively, raising the mean.
When the CORE1–CORE2 link is removed the failure penalty (+15 ms) is applied
and BS4/BS5 become unreachable, adding two unreachable-site penalties (+40 ms total),
which is why failure mode pushes delay well above the 80 ms KPI limit immediately.
            """)
        section_end()

    # ── 3. Coverage & Power ───────────────────────────────────────────────────
    with tabs[2]:
        section_start("Coverage & Received Power",
                       "Path loss, received power, and 2-D downlink coverage map.")
        st.markdown("#### Received Power at Sample Distances")
        wireless_df = pd.DataFrame(wireless_results)
        st.dataframe(wireless_df, use_container_width=True)

        col_chart, col_map = st.columns(2)
        c = _mpl_colors()

        with col_chart:
            st.markdown("#### Path Loss vs Distance")
            if not wireless_df.empty:
                st.line_chart(
                    wireless_df.set_index("distance_km")["path_loss_db"],
                    height=360,
                )

        with col_map:
            st.markdown("#### 2-D Coverage Map")
            coverage_data = compute_coverage_map(config)
            x = np.array(coverage_data["x_km"])
            y = np.array(coverage_data["y_km"])
            Z = np.array(coverage_data["rx_power_dbm"])
            t1 = coverage_data["threshold_1_dbm"]
            t2 = coverage_data["threshold_2_dbm"]

            # RF heatmaps are clearest on a dark background in both themes
            fig_cov, ax_cov = plt.subplots(figsize=(5.5, 5))
            fig_cov.patch.set_facecolor("#0d1b2a")
            ax_cov.set_facecolor("#0d1b2a")
            levels = np.linspace(float(Z.min()), max(float(Z.max()), -40), 28)
            cf = ax_cov.contourf(x, y, Z, levels=levels, cmap="RdYlGn")
            ax_cov.contour(x, y, Z, levels=[t1],
                           colors=["#22d3ee"], linestyles=["--"], linewidths=[1.8])
            ax_cov.contour(x, y, Z, levels=[t2],
                           colors=["#fbbf24"], linestyles=["--"], linewidths=[1.8])
            cbar = fig_cov.colorbar(cf, ax=ax_cov, shrink=0.85)
            cbar.set_label("Rx Power (dBm)", color="#e2e8f0")
            cbar.ax.yaxis.set_tick_params(color="#94a3b8")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#94a3b8")
            ax_cov.set_xlabel("East–West (km)", color="#cbd5e1")
            ax_cov.set_ylabel("North–South (km)", color="#cbd5e1")
            ax_cov.set_title("Downlink Coverage — Okumura-Hata 1800 MHz",
                             color="#f1f5f9", fontsize=10, fontweight="bold")
            ax_cov.tick_params(colors="#94a3b8")
            for sp in ax_cov.spines.values(): sp.set_edgecolor("#334155")
            ax_cov.set_aspect("equal")
            ax_cov.legend(
                handles=[
                    mlines.Line2D([], [], color="#22d3ee", linestyle="--",
                                  label=f"Edge threshold  {t1} dBm"),
                    mlines.Line2D([], [], color="#fbbf24", linestyle="--",
                                  label=f"Quality threshold {t2} dBm"),
                ],
                facecolor="#1e293b", labelcolor="#e2e8f0", fontsize=8,
            )
            st.pyplot(fig_cov)
            plt.close(fig_cov)

        for col, (title, val) in zip(st.columns(4), [
            ("Reuse Factor",         wireless_cfg.get("reuse_factor", reuse_factor)),
            ("Sector Count",         wireless_cfg.get("sector_count", sector_count)),
            ("BS Antenna Height (m)", wireless_cfg.get("base_height_m", 30)),
            ("UE Height (m)",         wireless_cfg.get("mobile_height_m", 1.5)),
        ]):
            with col: metric_card(title, val)
        st.info(
            "Cyan = sensitivity edge threshold. "
            "Amber = tighter quality threshold. "
            "Increasing antenna height or adding sites extends coverage; "
            "reducing reuse factor improves capacity at the cost of interference."
        )
        section_end()

    # ── 4. Microwave Backhaul ─────────────────────────────────────────────────
    with tabs[3]:
        section_start("Microwave Backhaul",
                       "Full point-to-point link budget for every backhaul segment.")
        st.markdown("#### Link Budget Table")
        lb_df = build_link_budget_df(backhaul_results)
        if not lb_df.empty:
            st.dataframe(lb_df, use_container_width=True)
        else:
            st.info("No microwave link budget parameters found in configuration.")
        st.markdown("#### Link Capacity")
        net_df = build_network_links_df(backhaul_results)
        if not net_df.empty and "Capacity (Mbps)" in net_df.columns:
            st.bar_chart(net_df.set_index("Link")["Capacity (Mbps)"], height=300)
        st.markdown("#### Failure State")
        st.json(failed_info)
        section_end()

    # ── 5. Teletraffic & Erlang B ─────────────────────────────────────────────
    with tabs[4]:
        section_start("Teletraffic & Erlang B",
                       "Voice traffic dimensioning and blocking probability at the current load.")
        tt = teletraffic_results
        c = _mpl_colors()

        for col, (title, val) in zip(st.columns(4), [
            ("Voice Offered (Erl)", tt["voice_erlangs"]),
            ("Voice Channels",      tt["voice_channels"]),
            ("Blocking (%)",        tt["blocking_percent"]),
            ("Blocking Status",     tt["status"]),
        ]):
            with col: metric_card(title, val)

        if tt["status"] == "FAIL":
            st.error(
                f"Blocking {tt['blocking_percent']}% exceeds target "
                f"{tt['target_blocking_percent']}%. "
                f"Minimum channels required: **{tt['min_channels_for_target']}**."
            )
        else:
            st.success(
                f"Blocking {tt['blocking_percent']}% is within the "
                f"{tt['target_blocking_percent']}% target."
            )

        col_curve, col_traf = st.columns([1.3, 1])

        with col_curve:
            st.markdown("#### Erlang B Dimensioning Curve")
            curve_df = pd.DataFrame(tt["erlang_b_curve"])
            if not curve_df.empty:
                fig2, ax2 = plt.subplots(figsize=(6, 4.2))
                _style_ax(ax2, fig2, c,
                          title=f"Erlang B — A = {tt['voice_erlangs']} Erl",
                          xlabel="Number of channels",
                          ylabel="Blocking probability (%)")
                ax2.plot(curve_df["channels"], curve_df["blocking_percent"],
                         color=c["accent1"], linewidth=2, marker="o", markersize=4)
                ax2.axhline(tt["target_blocking_percent"],
                            color=c["warning"], linestyle="--", linewidth=1.5,
                            label=f"Target {tt['target_blocking_percent']}%")
                ax2.axvline(tt["voice_channels"],
                            color=c["accent3"], linestyle=":", linewidth=1.5,
                            label=f"Current channels ({tt['voice_channels']})")
                ax2.legend(facecolor=c["sec_bg"], labelcolor=c["text"], fontsize=9)
                st.pyplot(fig2)
                plt.close(fig2)

        with col_traf:
            st.markdown("#### Traffic Class Summary")
            st.dataframe(pd.DataFrame(tt["traffic_summary"]),
                         use_container_width=True, height=240)
            metric_card("Min Channels for Target", tt["min_channels_for_target"])

        section_end()

    # ── 6. Signaling & Setup Delay ────────────────────────────────────────────
    with tabs[5]:
        section_start("Signaling & Call Setup Delay",
                       "Per-hop M/D/1 queue model — setup latency at current load and under burst.")
        sig = signaling_results
        c = _mpl_colors()

        st.markdown("#### Per-Base-Station Setup Delay")
        if sig["per_bs_delays"]:
            st.dataframe(pd.DataFrame(sig["per_bs_delays"]),
                         use_container_width=True)

        st.markdown("#### Burst Sweep — Individual Base Station Charts")
        burst_df = pd.DataFrame(sig["burst_sweep"])
        if not burst_df.empty and "setup_delay_ms" in burst_df.columns:
            bs_list = list(burst_df["base_station"].unique())
            n_bs = len(bs_list)
            n_cols = 3
            n_rows = (n_bs + n_cols - 1) // n_cols
            palette = ["#38bdf8", "#a78bfa", "#34d399", "#fb923c", "#f472b6", "#facc15"]

            fig3, axes = plt.subplots(n_rows, n_cols,
                                      figsize=(13, 4.2 * n_rows),
                                      squeeze=False)
            fig3.patch.set_facecolor(c["sec_bg"])

            for i, bs in enumerate(bs_list):
                row, col = divmod(i, n_cols)
                ax = axes[row][col]
                bs_data = burst_df[burst_df["base_station"] == bs]
                valid   = bs_data.dropna(subset=["setup_delay_ms"])
                invalid = bs_data[bs_data["setup_delay_ms"].isna()]

                _style_ax(ax, fig3, c,
                          title=f"{bs}  ({valid.shape[0]}/{bs_data.shape[0]} points)",
                          xlabel="Load Factor",
                          ylabel="Setup Delay (ms)")

                if not valid.empty:
                    ax.plot(valid["load_factor"], valid["setup_delay_ms"],
                            color=palette[i % len(palette)],
                            linewidth=2, marker="o", markersize=5)

                # Mark saturation point with a vertical red dashed line
                if not invalid.empty:
                    sat_load = invalid["load_factor"].min()
                    ax.axvline(sat_load, color="#f87171", linestyle="--",
                               linewidth=1.5, label=f"Saturated ×{sat_load}")
                    ax.legend(facecolor=c["sec_bg"], labelcolor=c["text"],
                              fontsize=8)

            # Hide any unused subplot panels
            for j in range(n_bs, n_rows * n_cols):
                row, col = divmod(j, n_cols)
                axes[row][col].set_visible(False)

            fig3.tight_layout(pad=2.0)
            st.pyplot(fig3)
            plt.close(fig3)

        st.info(
            "Each panel shows one base station independently so saturation on "
            "one path never collapses the scale of others. "
            "A red dashed line marks the load factor where the link queue saturates "
            "(delay → ∞). BS4 and BS5 saturate earlier because their paths "
            "traverse two hops (via CORE2 → CORE1)."
        )
        section_end()

    # ── 7. Forecasting ────────────────────────────────────────────────────────
    with tabs[6]:
        section_start("Forecasting",
                       "Traffic growth outlook and phased upgrade recommendation.")
        forecast_df = pd.DataFrame(forecast_results)
        st.dataframe(forecast_df, use_container_width=True)
        if not forecast_df.empty:
            st.markdown("#### Current vs Forecast Load")
            st.bar_chart(
                forecast_df.set_index("class")[["current_load", "forecast_load"]],
                height=380,
            )
        overloaded = forecast_df[forecast_df["forecast_load"] > 100]
        if len(overloaded):
            st.warning("Phased upgrade recommended for classes projected above 100 load units.")
            st.dataframe(overloaded, use_container_width=True)
        else:
            st.success("No forecast-based upgrade trigger detected.")
        section_end()

    # ── 8. Stress & Failure ───────────────────────────────────────────────────
    with tabs[7]:
        section_start(
            "Stress Testing & Baseline vs Failure Comparison",
            "Breaking-point study and side-by-side QoS impact of the CORE1-CORE2 failure.",
        )
        c = _mpl_colors()

        # Comparison table
        st.markdown("#### Baseline vs Failure — Current Load Multiplier")
        base_q = comparison_results["baseline"]
        fail_q = comparison_results["failure"]
        cmp_rows = []
        for label, key in [
            ("Avg Delay (ms)",      "average_delay_ms"),
            ("Jitter (ms)",         "average_jitter_ms"),
            ("Throughput (Mbps)",   "throughput_mbps"),
            ("Packet Loss (%)",     "packet_loss_percent"),
            ("Voice Blocking (%)",  "voice_blocking_percent"),
            ("Availability (%)",    "site_availability_percent"),
        ]:
            bv = base_q.get(key, "N/A")
            fv = fail_q.get(key, "N/A")
            delta = (
                round(float(fv) - float(bv), 3)
                if isinstance(bv, (int, float)) and isinstance(fv, (int, float))
                else "N/A"
            )
            cmp_rows.append({"Metric": label, "Baseline": bv,
                             "Failure": fv, "Delta (failure-baseline)": delta})
        st.dataframe(pd.DataFrame(cmp_rows), use_container_width=True)

        # Side-by-side bar charts
        fig4, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(10, 4))
        for ax in (ax_l, ax_r):
            _style_ax(ax, fig4, c)
        bar_c = [c["accent1"], c["accent2"]]
        ax_l.bar(["Baseline","Failure"],
                 [base_q["average_delay_ms"], fail_q["average_delay_ms"]],
                 color=bar_c, width=0.45)
        ax_l.axhline(kpi_targets.get("max_delay_ms_critical", 80),
                     color=c["warning"], linestyle="--", linewidth=1.5,
                     label="KPI limit")
        ax_l.set_title("Average Delay (ms)", color=c["text"])
        ax_l.set_ylabel("ms", color=c["text"])
        ax_l.legend(facecolor=c["sec_bg"], labelcolor=c["text"], fontsize=9)

        ax_r.bar(["Baseline","Failure"],
                 [base_q["throughput_mbps"], fail_q["throughput_mbps"]],
                 color=bar_c, width=0.45)
        ax_r.axhline(kpi_targets.get("min_throughput_mbps", 180),
                     color=c["warning"], linestyle="--", linewidth=1.5,
                     label="KPI limit")
        ax_r.set_title("Throughput (Mbps)", color=c["text"])
        ax_r.set_ylabel("Mbps", color=c["text"])
        ax_r.legend(facecolor=c["sec_bg"], labelcolor=c["text"], fontsize=9)

        st.pyplot(fig4)
        plt.close(fig4)

        st.markdown("---")

        # Breaking-point study
        st.markdown("#### Breaking-Point Stress Test")
        stress_df = build_stress_dataframe(stress_results)
        if not stress_df.empty:
            st.dataframe(stress_df, use_container_width=True)

        first_fail  = stress_results.get("first_failure_multiplier")
        failed_kpis = stress_results.get("failed_kpis", [])
        for col, (title, val) in zip(st.columns(2), [
            ("First Failure Multiplier",
             first_fail if first_fail is not None else "No failure detected"),
            ("Failed KPIs",
             ", ".join(failed_kpis) if failed_kpis else "None"),
        ]):
            with col: metric_card(title, val)

        if first_fail is not None:
            st.error(
                f"First KPI failure at load multiplier **{first_fail}**. "
                f"Failed KPIs: {', '.join(failed_kpis)}"
            )
        else:
            st.success("No KPI failure detected within the tested load range.")

        section_end()

    st.markdown("---")
    st.caption("TELE527 Group 2 · Private Industrial LTE Network · BIUST")
