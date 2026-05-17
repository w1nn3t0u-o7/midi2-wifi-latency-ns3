#!/usr/bin/env python3
"""
MIDI 2.0 Wi-Fi Simulation - Result Plotter
Reads CSVs from midi_results/ and produces per-scenario plots.
Usage: python plot_results.py [results_dir]
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

RESULTS_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.expanduser("~"), "Projects", "midi2-wifi-latency-ns3", "results"
)
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

STANDARDS = ["80211ac", "80211ax", "80211be"]
STD_LABELS = {"80211ac": "Wi-Fi 5 (802.11ac)", "80211ax": "Wi-Fi 6 (802.11ax)", "80211be": "Wi-Fi 7 (802.11be)"}
STD_COLORS = {"80211ac": "#E07B39", "80211ax": "#3A7DC9", "80211be": "#2CA02C"}
LATENCY_LIMIT = 10.0   # ms — MIDI perceptible threshold
LATENCY_MAX   = 20.0   # ms — MIDI acceptable maximum

MIDI_COLOR = "#E07B39"

def load_csv(name):
    path = os.path.join(RESULTS_DIR, name)
    if not os.path.exists(path):
        print(f"[WARN] Missing: {path}")
        return None
    df = pd.read_csv(path)
    df["meanDelay_ms"] = pd.to_numeric(df["meanDelay_ms"], errors="coerce")
    df["jitter_ms"]    = pd.to_numeric(df["jitter_ms"],    errors="coerce")
    df["lossRate_pct"] = pd.to_numeric(df["lossRate_pct"], errors="coerce")
    df["param_value"]  = pd.to_numeric(df["param_value"],  errors="coerce")
    return df

def aggregate(df, param_col="param_value"):
    """Mean delay + jitter aggregated across all flows per (standard, param)."""
    return (df.groupby(["standard", param_col])
              .agg(meanDelay=("meanDelay_ms", "mean"),
                   meanJitter=("jitter_ms",   "mean"),
                   lossRate  =("lossRate_pct","mean"))
              .reset_index())

def add_thresholds(ax):
    ax.axhline(LATENCY_LIMIT, color="gold",   linestyle="--", linewidth=1.2, label=f"Perceptible ({LATENCY_LIMIT} ms)")
    ax.axhline(LATENCY_MAX,   color="tomato", linestyle="--", linewidth=1.2, label=f"Max acceptable ({LATENCY_MAX} ms)")

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
    ax.spines[["top","right"]].set_visible(False)

# ---------------------------------------------------------------
# SCENARIO 1 — Network Capacity
# ---------------------------------------------------------------
def plot_scenario1():
    df = load_csv("scenario1_capacity.csv")
    if df is None: return
    agg = aggregate(df)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=False)
    fig.suptitle("Scenario 1 — Network Capacity: MIDI Nodes vs. Latency", fontsize=14, fontweight="bold")

    metrics = [
        ("meanDelay", "Mean Delay (ms)",  "scenario1_capacity_delay.png"),
        ("meanJitter","Mean Jitter (ms)", None),
        ("lossRate",  "Packet Loss (%)",  None),
    ]

    for ax, (col, ylabel, _) in zip(axes, metrics):
        for std in STANDARDS:
            sub = agg[agg["standard"] == std].sort_values("param_value")
            ax.plot(sub["param_value"], sub[col],
                    marker="o", label=STD_LABELS[std],
                    color=STD_COLORS[std], linewidth=2, markersize=6)
        if col == "meanDelay":
            add_thresholds(ax)
        style_ax(ax, ylabel, "Number of MIDI Nodes", ylabel)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, fontsize=9,
               bbox_to_anchor=(0.5, -0.04), frameon=False)
    fig.tight_layout()
    save(fig, "scenario1_capacity.png")

# ---------------------------------------------------------------
# SCENARIO 2 — Background Noise
# ---------------------------------------------------------------
def plot_scenario2():
    df = load_csv("scenario2_background.csv")
    if df is None: return
    agg = aggregate(df)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=False)
    fig.suptitle("Scenario 2 — Background Noise Impact: Interferers vs. Latency", fontsize=14, fontweight="bold")

    metrics = [
        ("meanDelay", "Mean Delay (ms)"),
        ("meanJitter","Mean Jitter (ms)"),
        ("lossRate",  "Packet Loss (%)"),
    ]

    for ax, (col, ylabel) in zip(axes, metrics):
        for std in STANDARDS:
            sub = agg[agg["standard"] == std].sort_values("param_value")
            ax.plot(sub["param_value"], sub[col],
                    marker="s", label=STD_LABELS[std],
                    color=STD_COLORS[std], linewidth=2, markersize=6)
        if col == "meanDelay":
            add_thresholds(ax)
        style_ax(ax, ylabel, "Number of Background Nodes", ylabel)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, fontsize=9,
               bbox_to_anchor=(0.5, -0.04), frameon=False)
    fig.tight_layout()
    save(fig, "scenario2_background.png")

# ---------------------------------------------------------------
# SCENARIO 3 — Distance
# ---------------------------------------------------------------
def plot_scenario3():
    df = load_csv("scenario3_distance.csv")
    if df is None: return
    agg = aggregate(df)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=False)
    fig.suptitle("Scenario 3 — Distance Impact: AP–STA Range vs. Latency", fontsize=14, fontweight="bold")

    metrics = [
        ("meanDelay", "Mean Delay (ms)"),
        ("meanJitter","Mean Jitter (ms)"),
        ("lossRate",  "Packet Loss (%)"),
    ]

    for ax, (col, ylabel) in zip(axes, metrics):
        for std in STANDARDS:
            sub = agg[agg["standard"] == std].sort_values("param_value")
            ax.plot(sub["param_value"], sub[col],
                    marker="^", label=STD_LABELS[std],
                    color=STD_COLORS[std], linewidth=2, markersize=6)
        if col == "meanDelay":
            add_thresholds(ax)
        style_ax(ax, ylabel, "Distance (m)", ylabel)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, fontsize=9,
               bbox_to_anchor=(0.5, -0.04), frameon=False)
    fig.tight_layout()
    save(fig, "scenario3_distance.png")

# ---------------------------------------------------------------
# COMBINED OVERVIEW — one delay plot per scenario, all standards
# ---------------------------------------------------------------
def plot_overview():
    files = {
        "Capacity (nMidi)":    ("scenario1_capacity.csv",   "param_value", "Number of MIDI Nodes"),
        "Background (nBG)":    ("scenario2_background.csv", "param_value", "Background Nodes"),
        "Distance (m)":        ("scenario3_distance.csv",   "param_value", "Distance (m)"),
    }

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    fig.suptitle("MIDI 2.0 over 802.11 — Mean Delay Overview", fontsize=14, fontweight="bold")

    for ax, (title, (fname, xcol, xlabel)) in zip(axes, files.items()):
        df = load_csv(fname)
        if df is None:
            ax.set_visible(False)
            continue
        agg = aggregate(df, xcol)
        for std in STANDARDS:
            sub = agg[agg["standard"] == std].sort_values(xcol)
            ax.plot(sub[xcol], sub["meanDelay"],
                    marker="o", label=STD_LABELS[std],
                    color=STD_COLORS[std], linewidth=2.2, markersize=6)
        add_thresholds(ax)
        style_ax(ax, title, xlabel, "Mean Delay (ms)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, fontsize=9,
               bbox_to_anchor=(0.5, -0.04), frameon=False)
    fig.tight_layout()
    save(fig, "overview_delay.png")

if __name__ == "__main__":
    print(f"Reading results from: {RESULTS_DIR}")
    print(f"Saving plots to:      {PLOTS_DIR}")
    plot_scenario1()
    plot_scenario2()
    plot_scenario3()
    plot_overview()
    print("Done.")
