import os
import matplotlib.pyplot as plt


def ensure_output_dirs():
    os.makedirs("outputs/figures", exist_ok=True)


def plot_stress_test_results(stress_results: dict, scenario_name: str = "baseline"):
    ensure_output_dirs()

    history = stress_results.get("history", [])
    if not history:
        print("No stress test history to plot.")
        return

    load_multipliers = [entry["load_multiplier"] for entry in history]
    delays = [entry["qos_results"]["average_delay_ms"] for entry in history]
    packet_losses = [entry["qos_results"]["packet_loss_percent"] for entry in history]
    throughputs = [entry["qos_results"]["throughput_mbps"] for entry in history]
    availabilities = [entry["qos_results"]["site_availability_percent"] for entry in history]

    # Plot 1: Delay vs Load
    plt.figure(figsize=(8, 5))
    plt.plot(load_multipliers, delays, marker="o", label="Average Delay (ms)")
    plt.axhline(80, linestyle="--", label="Delay KPI Limit (80 ms)")
    plt.xlabel("Load Multiplier")
    plt.ylabel("Average Delay (ms)")
    plt.title(f"Stress Test: Delay vs Load ({scenario_name})")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"outputs/figures/stress_delay_{scenario_name}.png", dpi=300)
    plt.close()

    # Plot 2: Packet Loss vs Load
    plt.figure(figsize=(8, 5))
    plt.plot(load_multipliers, packet_losses, marker="o", label="Packet Loss (%)")
    plt.axhline(2.5, linestyle="--", label="Packet Loss KPI Limit (2.5%)")
    plt.xlabel("Load Multiplier")
    plt.ylabel("Packet Loss (%)")
    plt.title(f"Stress Test: Packet Loss vs Load ({scenario_name})")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"outputs/figures/stress_packet_loss_{scenario_name}.png", dpi=300)
    plt.close()

    # Plot 3: Throughput vs Load
    plt.figure(figsize=(8, 5))
    plt.plot(load_multipliers, throughputs, marker="o", label="Throughput (Mbps)")
    plt.axhline(180, linestyle="--", label="Minimum Throughput KPI (180 Mbps)")
    plt.xlabel("Load Multiplier")
    plt.ylabel("Throughput (Mbps)")
    plt.title(f"Stress Test: Throughput vs Load ({scenario_name})")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"outputs/figures/stress_throughput_{scenario_name}.png", dpi=300)
    plt.close()

    # Plot 4: Availability vs Load
    plt.figure(figsize=(8, 5))
    plt.plot(load_multipliers, availabilities, marker="o", label="Site Availability (%)")
    plt.axhline(80, linestyle="--", label="Minimum Availability KPI (80%)")
    plt.xlabel("Load Multiplier")
    plt.ylabel("Site Availability (%)")
    plt.title(f"Stress Test: Site Availability vs Load ({scenario_name})")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"outputs/figures/stress_availability_{scenario_name}.png", dpi=300)
    plt.close()

    print(f"Stress test plots saved for scenario: {scenario_name}")