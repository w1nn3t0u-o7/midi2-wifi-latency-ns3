#!/usr/bin/env python3
"""
MIDI 2.0 Wi-Fi Simulation - Result Plotter
Reads CSVs produced by run_scenarios.sh (multi-RngRun format) and produces
per-scenario plots with 95% confidence intervals across RNG runs.

CSV columns expected:
  scenario, standard, param_name, param_value, rng_run,
  flow_id, src, dst, txPkts, rxPkts, lost,
  lossRate_pct, meanDelay_ms, jitter_ms

Usage: python plot_results.py [results_dir]
"""

import sys
import os
import warnings
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from scipy import stats

warnings.filterwarnings("ignore", category=RuntimeWarning)

RESULTS_DIR = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(
        os.path.expanduser("~"), "Projects", "midi2-wifi-latency-ns3", "results"
    )
)

PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

STANDARDS = ["80211ac", "80211ax", "80211be"]
STD_LABELS = {
    "80211ac": "Wi-Fi 5 (802.11ac)",
    "80211ax": "Wi-Fi 6 (802.11ax)",
    "80211be": "Wi-Fi 7 (802.11be)",
}
STD_COLORS = {"80211ac": "#E07B39", "80211ax": "#3A7DC9", "80211be": "#2CA02C"}

LATENCY_LIMIT = 10.0  # ms — MIDI perceptible threshold
CI_ALPHA = 0.05  # 95 % confidence intervals


# ---------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------
def load_csv(name):
    path = os.path.join(RESULTS_DIR, name)
    if not os.path.exists(path):
        print(f"[WARN] Missing: {path}")
        return None
    df = pd.read_csv(path)
    for col in ("meanDelay_ms", "jitter_ms", "lossRate_pct", "param_value"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def save(fig, name):
    path = os.path.join(PLOTS_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def style_ax(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.spines[["top", "right"]].set_visible(False)


def add_thresholds(ax):
    ax.axhline(
        LATENCY_LIMIT,
        color="tomato",
        linestyle="--",
        linewidth=1.2,
        label=f"Max acceptable ({LATENCY_LIMIT} ms)",
    )


# ---------------------------------------------------------------
# Aggregation with 95 % CI
# First average each (standard, param_value, rng_run) across all flows,
# then compute mean ± CI across rng_runs.
# ---------------------------------------------------------------
def aggregate_with_ci(df, param_col="param_value"):
    """
    Returns a DataFrame with columns:
      standard, <param_col>,
      meanDelay, delay_ci,
      meanJitter, jitter_ci,
      lossRate,  loss_ci
    where *_ci is the half-width of the 95% t-distribution CI.
    """
    # Step 1: per-run mean (average over flows within one run)
    per_run = (
        df.groupby(["standard", param_col, "rng_run"])
        .agg(
            delay=("meanDelay_ms", "mean"),
            jitter=("jitter_ms", "mean"),
            loss=("lossRate_pct", "mean"),
        )
        .reset_index()
    )

    records = []
    for (std, pval), grp in per_run.groupby(["standard", param_col]):
        n = len(grp)
        for metric, col in [("delay", "delay"), ("jitter", "jitter"), ("loss", "loss")]:
            vals = grp[col].dropna().values
            mean = vals.mean() if len(vals) else np.nan
            if len(vals) >= 2:
                # t-distribution CI
                se = stats.sem(vals)
                h = se * stats.t.ppf(1 - CI_ALPHA / 2, df=len(vals) - 1)
            else:
                h = np.nan
            records.append(
                {
                    "standard": std,
                    param_col: pval,
                    f"mean_{metric}": mean,
                    f"ci_{metric}": h,
                }
            )

    # Pivot: one row per (standard, param_value), columns for each metric
    out = {}
    for r in records:
        key = (r["standard"], r[param_col])
        if key not in out:
            out[key] = {"standard": r["standard"], param_col: r[param_col]}
        for k, v in r.items():
            if k not in ("standard", param_col):
                out[key][k] = v

    return pd.DataFrame(list(out.values()))


# ---------------------------------------------------------------
# Generic plot builder — shared by all three scenarios
# ---------------------------------------------------------------
def plot_scenario(
    csv_name, scenario_title, xlabel, x_col, output_name, marker="o", x_integer=True
):
    df = load_csv(csv_name)
    if df is None:
        return

    agg = aggregate_with_ci(df, x_col)

    metrics = [
        ("mean_delay", "ci_delay", "Mean Delay (ms)"),
        ("mean_jitter", "ci_jitter", "Mean Jitter (ms)"),
        ("mean_loss", "ci_loss", "Packet Loss (%)"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=False)
    fig.suptitle(scenario_title, fontsize=14, fontweight="bold")

    for ax, (col, ci_col, ylabel) in zip(axes, metrics):
        for std in STANDARDS:
            sub = agg[agg["standard"] == std].sort_values(x_col)
            x = sub[x_col].values
            y = sub[col].values
            ci = sub[ci_col].values

            ax.plot(
                x,
                y,
                marker=marker,
                label=STD_LABELS[std],
                color=STD_COLORS[std],
                linewidth=2,
                markersize=6,
                zorder=3,
            )

            # Shade CI band; fall back gracefully if all NaN
            valid = ~np.isnan(ci) & ~np.isnan(y)
            if valid.any():
                ax.fill_between(
                    x[valid],
                    (y - ci)[valid],
                    (y + ci)[valid],
                    color=STD_COLORS[std],
                    alpha=0.15,
                    zorder=2,
                )

        if col == "mean_delay":
            add_thresholds(ax)

        style_ax(ax, ylabel, xlabel, ylabel)
        if x_integer:
            ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=5,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.04),
        frameon=False,
    )
    fig.tight_layout()
    save(fig, output_name)


# ---------------------------------------------------------------
# Scenario functions
# ---------------------------------------------------------------
def plot_scenario1():
    plot_scenario(
        csv_name="scenario1_capacity.csv",
        scenario_title="Scenario 1 — Network Capacity: MIDI Nodes vs. Latency",
        xlabel="Number of MIDI Nodes",
        x_col="param_value",
        output_name="scenario1_capacity.png",
        marker="o",
    )


def plot_scenario2():
    plot_scenario(
        csv_name="scenario2_background.csv",
        scenario_title="Scenario 2 — Background Noise: Interferers vs. Latency",
        xlabel="Number of Background Nodes",
        x_col="param_value",
        output_name="scenario2_background.png",
        marker="s",
    )


def plot_scenario3():
    plot_scenario(
        csv_name="scenario3_distance.csv",
        scenario_title="Scenario 3 — Distance: AP–STA Range vs. Latency",
        xlabel="Distance (m)",
        x_col="param_value",
        output_name="scenario3_distance.png",
        marker="^",
        x_integer=False,
    )


# ---------------------------------------------------------------
# Combined overview — mean delay only, all three scenarios
# ---------------------------------------------------------------
def plot_overview():
    configs = [
        (
            "scenario1_capacity.csv",
            "param_value",
            "Number of MIDI Nodes",
            "Capacity (nMidi)",
        ),
        (
            "scenario2_background.csv",
            "param_value",
            "Background Nodes",
            "Background (nBG)",
        ),
        ("scenario3_distance.csv", "param_value", "Distance (m)", "Distance (m)"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    fig.suptitle(
        "MIDI 2.0 over 802.11 — Mean Delay Overview (95% CI)",
        fontsize=14,
        fontweight="bold",
    )

    for ax, (fname, xcol, xlabel, title) in zip(axes, configs):
        df = load_csv(fname)
        if df is None:
            ax.set_visible(False)
            continue
        agg = aggregate_with_ci(df, xcol)
        for std in STANDARDS:
            sub = agg[agg["standard"] == std].sort_values(xcol)
            x = sub[xcol].values
            y = sub["mean_delay"].values
            ci = sub["ci_delay"].values

            ax.plot(
                x,
                y,
                marker="o",
                label=STD_LABELS[std],
                color=STD_COLORS[std],
                linewidth=2.2,
                markersize=6,
                zorder=3,
            )
            valid = ~np.isnan(ci) & ~np.isnan(y)
            if valid.any():
                ax.fill_between(
                    x[valid],
                    (y - ci)[valid],
                    (y + ci)[valid],
                    color=STD_COLORS[std],
                    alpha=0.15,
                    zorder=2,
                )
        add_thresholds(ax)
        style_ax(ax, title, xlabel, "Mean Delay (ms)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=5,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.04),
        frameon=False,
    )
    fig.tight_layout()
    save(fig, "overview_delay.png")


# ---------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------
if __name__ == "__main__":
    print(f"Reading results from : {RESULTS_DIR}")
    print(f"Saving plots to      : {PLOTS_DIR}")
    plot_scenario1()
    plot_scenario2()
    plot_scenario3()
    plot_overview()
    print("Done.")
