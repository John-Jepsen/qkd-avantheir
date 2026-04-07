"""
BB84 QKD Protocol — Professional Visualizations

Produces four figures:
  1. Quantum circuit diagram (4-qubit example, both bases)
  2. QBER comparison across scenarios (bar chart with error bands)
  3. Depolarizing noise effect on QBER vs. error_rate sweep
  4. Sifting & key yield funnel across scenarios

Run:
    python visualize_bb84.py

Requires:
    pip install matplotlib pylatexenc
"""

import sys
import statistics
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

from qiskit import QuantumCircuit
from qiskit.visualization import plot_histogram
from bb84_simulator import BB84Protocol, QiskitQuantumChannel, _BATCH_SIZE

matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 130,
})

PALETTE = {
    "safe":    "#2196F3",   # blue
    "noisy":   "#FF9800",   # orange
    "eve":     "#F44336",   # red
    "neutral": "#78909C",   # grey
    "key":     "#4CAF50",   # green
}


# ── Figure 1: Quantum circuit diagram ───────────────────────────────────────

def fig_circuit_diagram():
    """Draw a 4-qubit BB84 circuit: Z-basis bit-1, X-basis bit-0,
    noise id gate, and X-basis measurement.  Annotated with role labels."""

    qc = QuantumCircuit(4, 4)
    qc.barrier(label="Alice prepares")

    # Qubit 0: bit=1, Z-basis  →  just X gate
    qc.x(0)
    # Qubit 1: bit=0, Z-basis  →  no gate (|0⟩)
    # Qubit 2: bit=1, X-basis  →  X then H
    qc.x(2)
    qc.h(2)
    # Qubit 3: bit=0, X-basis  →  just H
    qc.h(3)

    qc.barrier(label="Channel noise")
    for i in range(4):
        qc.id(i)

    qc.barrier(label="Bob measures")
    # Bob bases: Z, X, Z, X
    qc.h(1)   # Bob chose X for qubit 1
    qc.h(3)   # Bob chose X for qubit 3
    for i in range(4):
        qc.measure(i, i)

    fig = qc.draw("mpl", style="iqp", fold=-1, plot_barriers=True)
    fig.suptitle(
        "Figure 1 — BB84 Quantum Circuit (4-qubit example)\n"
        "Alice: qubits 0–3 | id = depolarizing noise gate | Bob measures",
        fontsize=12, fontweight="bold", y=1.02,
    )
    fig.tight_layout()
    fig.savefig("fig1_circuit.png", bbox_inches="tight")
    print("  Saved fig1_circuit.png")
    return fig


# ── Figure 2: QBER comparison ───────────────────────────────────────────────

def fig_qber_comparison(n_trials: int = 8, n_bits: int = 2048):
    """Run each scenario n_trials times and plot QBER mean ± std."""

    scenarios = [
        ("Normal\n(1% noise)",        {"error_rate": 0.01, "eavesdrop": False}, PALETTE["safe"]),
        ("Noisy\n(5% noise)",          {"error_rate": 0.05, "eavesdrop": False}, PALETTE["noisy"]),
        ("Eavesdropper\n(~25% QBER)",  {"error_rate": 0.01, "eavesdrop": True},  PALETTE["eve"]),
    ]

    print("  Running QBER trials (this may take ~30 s) …")
    means, stds, labels, colors = [], [], [], []
    for label, kwargs, color in scenarios:
        qbers = []
        for _ in range(n_trials):
            r = BB84Protocol(**kwargs, backend="classical").run(n_bits=n_bits)
            qbers.append(r.qber)
        means.append(statistics.mean(qbers))
        stds.append(statistics.stdev(qbers) if len(qbers) > 1 else 0)
        labels.append(label)
        colors.append(color)

    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.arange(len(labels))
    bars = ax.bar(x, means, yerr=stds, color=colors, width=0.5,
                  capsize=8, error_kw={"linewidth": 2, "ecolor": "#333"}, zorder=3)

    ax.axhline(0.11, color="#E53935", linestyle="--", linewidth=1.5, label="Abort threshold (11%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Estimated QBER")
    ax.set_ylim(0, max(means) * 1.4 + 0.05)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=0))
    ax.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    ax.legend(frameon=False)

    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + std + 0.005,
                f"{mean:.1%}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_title("Figure 2 — QBER by Scenario (mean ± std, n={})".format(n_trials))
    fig.tight_layout()
    fig.savefig("fig2_qber_comparison.png", bbox_inches="tight")
    print("  Saved fig2_qber_comparison.png")
    return fig


# ── Figure 3: QBER vs. noise sweep ──────────────────────────────────────────

def fig_noise_sweep(n_bits: int = 1024):
    """Plot measured QBER vs. configured error_rate to validate the
    depolarizing noise model and show the eavesdropper baseline."""

    error_rates = np.linspace(0.0, 0.25, 18)
    qbers_clean, qbers_eve = [], []

    print("  Running noise sweep …")
    for er in error_rates:
        r = BB84Protocol(error_rate=float(er), eavesdrop=False, backend="classical").run(n_bits)
        qbers_clean.append(r.qber)
        r2 = BB84Protocol(error_rate=float(er), eavesdrop=True, backend="classical").run(n_bits)
        qbers_eve.append(r2.qber)

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(error_rates * 100, [q * 100 for q in qbers_clean],
            "o-", color=PALETTE["safe"], linewidth=2, markersize=5, label="No eavesdropper")
    ax.plot(error_rates * 100, [q * 100 for q in qbers_eve],
            "s--", color=PALETTE["eve"], linewidth=2, markersize=5, label="Eavesdropper (intercept-resend)")
    ax.axhline(11, color="#E53935", linestyle=":", linewidth=1.5, label="Abort threshold 11%")
    ax.fill_between(error_rates * 100, 11, 100, alpha=0.06, color=PALETTE["eve"])

    ax.set_xlabel("Configured Channel Error Rate (%)")
    ax.set_ylabel("Measured QBER (%)")
    ax.set_xlim(0, 25)
    ax.set_ylim(0, 60)
    ax.grid(linestyle=":", alpha=0.4)
    ax.legend(frameon=False)
    ax.set_title("Figure 3 — Measured QBER vs. Channel Error Rate")

    # Annotate the ~25% Eve floor
    ax.annotate("Eve raises\nQBER ≈ 25%",
                xy=(1, 26), xytext=(8, 35),
                arrowprops=dict(arrowstyle="->", color="#555"),
                fontsize=9, color="#555")

    fig.tight_layout()
    fig.savefig("fig3_noise_sweep.png", bbox_inches="tight")
    print("  Saved fig3_noise_sweep.png")
    return fig


# ── Figure 4: Key-yield funnel ───────────────────────────────────────────────

def fig_key_yield_funnel(n_bits: int = 4096):
    """Waterfall / funnel showing raw → sifted → sample-removed → final key
    bit counts for each scenario."""

    scenarios = [
        ("Normal (1%)",      {"error_rate": 0.01, "eavesdrop": False}, PALETTE["safe"]),
        ("Noisy (5%)",        {"error_rate": 0.05, "eavesdrop": False}, PALETTE["noisy"]),
        ("Eavesdropper",      {"error_rate": 0.01, "eavesdrop": True},  PALETTE["eve"]),
    ]

    stages = ["Raw qubits", "After sifting\n(~50%)", "After QBER\nsample (−10%)", "Final key\n(256 bit)"]
    fig, ax = plt.subplots(figsize=(9, 5))

    bar_width = 0.22
    x = np.arange(len(stages))

    for idx, (label, kwargs, color) in enumerate(scenarios):
        r = BB84Protocol(**kwargs, backend="classical").run(n_bits=n_bits)

        sample_size = max(10, int(r.sifted_bits * 0.10))
        post_sample = r.sifted_bits - sample_size
        key_bits = r.key_length_bits if r.secure else 0

        heights = [r.raw_bits, r.sifted_bits, post_sample, key_bits]
        offset = (idx - 1) * bar_width
        bars = ax.bar(x + offset, heights, width=bar_width, color=color,
                      alpha=0.85, label=label, zorder=3)

        for bar, val in zip(bars, heights):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 30,
                        f"{val:,}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=10)
    ax.set_ylabel("Bits")
    ax.set_ylim(0, n_bits * 1.15)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.grid(axis="y", linestyle=":", alpha=0.4, zorder=0)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title(f"Figure 4 — Key Yield Funnel  (n_bits = {n_bits:,})")

    fig.tight_layout()
    fig.savefig("fig4_key_yield.png", bbox_inches="tight")
    print("  Saved fig4_key_yield.png")
    return fig


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("Generating BB84 visualizations …\n")

    print("[1/4] Circuit diagram")
    fig_circuit_diagram()

    print("[2/4] QBER comparison")
    fig_qber_comparison()

    print("[3/4] Noise sweep")
    fig_noise_sweep()

    print("[4/4] Key yield funnel")
    fig_key_yield_funnel()

    print("\nDone. Four PNG files written to the implementation/ directory.")
    plt.show()
