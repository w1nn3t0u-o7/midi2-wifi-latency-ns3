# midi2-wifi-latency-ns3

**End-to-End Latency Analysis of Network MIDI 2.0 UDP Traffic over IEEE 802.11ac/ax/be**

*Metody Symulacyjne project — AGH University, ICT Master's programme*

---

## Project Overview

Simulates a wireless recording studio environment to determine whether Wi-Fi 5, 6, and 7 can meet the latency requirements of Network MIDI 2.0 (< 10 ms effective output latency) under varying MAC-layer configurations.

### Research Question

> Which MAC-layer parameters most significantly affect end-to-end latency and jitter of MIDI-sized UDP traffic, and does each Wi-Fi generation meet the 10 ms MIDI 2.0 viability threshold when optimally configured?

---

## Repository Structure

```
midi2-wifi-latency-ns3/
├── midi2-latency-sim.cc   # ns-3 simulation (copy to ns-3 scratch/)
├── run_ofat.sh            # OFAT parameter sweep automation script
├── analyse_results.py     # Post-processing, statistics, and plots
└── README.md
```

---

## Traffic Model

| Parameter          | Value                              |
|--------------------|-------------------------------------|
| Protocol           | UDP (Network MIDI 2.0)              |
| Payload size       | 12 bytes (UMP with JR Timestamp)    |
| Packet rate        | ~500 pkt/s (worst-case performance) |
| Inter-arrival      | CBR (2 ms) or Poisson (mean 2 ms)   |
| DSCP mapping       | AC_BE / AC_VI / AC_VO (configurable)|
| Background traffic | Saturating UDP bulk, AC_BE          |

---

## Topology

```
[Performer STA 1] ─┐
[Performer STA 2] ─┤
       ...         ├──> [AP] <── [Background STAs 1..K]
[Performer STA N] ─┤
                   └──> [DAW Host STA]
```

- All nodes within 15 m radius of AP
- Indoor log-distance + Nakagami-m fading (α = 3.0)
- Static (no mobility)

---

## Simulation Parameters

| Parameter       | Values tested                          | Baseline     |
|-----------------|----------------------------------------|--------------|
| Wi-Fi standard  | 802.11ac / 802.11ax / 802.11be         | 802.11ax     |
| EDCA class      | AC_BE, AC_VI, **AC_VO**                | AC_VO        |
| A-MPDU          | On, **Off**                            | Off          |
| RTS/CTS         | On, **Off**                            | Off          |
| MCS             | 2 (low), **5 (mid)**, 9 (high), -1 (auto) | 5          |
| Channel width   | 20, 40, **80**, 160 MHz (be only)      | 80 MHz       |
| MIDI performers | 1, 5, 10, 15, 20, 25, 30               | 5            |
| Background STAs | 0, 1, 2, **3**, 5, 10, 15              | 3            |
| Seeds           | 1–10                                   | —            |

---

## Metrics

| Metric               | Description                                                   |
|----------------------|---------------------------------------------------------------|
| `delay_mean_us`      | Mean per-packet end-to-end delay (µs)                         |
| `delay_p99_us`       | 99th percentile delay — jitter measure                        |
| `L_eff_us`           | Effective output latency = d_99 (JR Timestamp model)          |
| `jr_jitter_window_us`| Jitter window = d_99 − d_1 (JR buffer depth)                 |
| `lossRate`           | Fraction of MIDI packets lost                                 |
| `pass_hard_10ms`     | 1 if L_eff < 10 000 µs (professional MIDI threshold)         |
| `pass_soft_20ms`     | 1 if L_eff < 20 000 µs (marginal / casual use threshold)      |

### JR Timestamp Model

Network MIDI 2.0 receivers use Jitter Reduction Timestamps to absorb jitter
at the cost of added output latency. The effective output latency is:

    L_eff = d_99

This means high jitter directly increases the perceived latency a musician
hears, regardless of mean delay. Both mean delay and P99 are therefore
necessary metrics.

---

## Quick Start

### 1. Install dependencies

```bash
# ns-3: https://www.nsnam.org/releases/ns-3-47/
# Python: scipy, pandas, matplotlib
pip install pandas scipy matplotlib
```

### 2. Copy simulation to ns-3

```bash
cp midi2-latency-sim.cc /path/to/ns-allinone-3.47/ns-3.47/scratch/
cp run_ofat.sh /path/to/ns-allinone-3.47/ns-3.47/scratch/
```

### 3. Build

```bash
cd /path/to/ns-allinone-3.47/ns-3.47
./ns3 build
```

### 4. Single test run

```bash
./ns3 run "scratch/midi2-latency-sim \
    --standard=80211ax \
    --edca=VO \
    --ampdu=0 \
    --rts=0 \
    --mcs=5 \
    --channelWidth=80 \
    --nMidi=5 \
    --nBg=3 \
    --seed=1 \
    --simTime=30 \
    --outputDir=results"
```

### 5. Full OFAT sweep (all standards, 10 seeds)

```bash
chmod +x scratch/run_ofat.sh
NS3_ROOT=. bash scratch/run_ofat.sh
```

### 6. Analyse results

```bash
python3 analyse_results.py \
    --results results/all_runs.csv \
    --output plots/
```

---

## Output Files

| File                              | Contents                                       |
|-----------------------------------|------------------------------------------------|
| `results/all_runs.csv`            | One row per simulation run (aggregated stats)  |
| `results/<tag>.csv`               | Per-run parameter and statistics summary       |
| `results/<tag>_packets.csv`       | Per-packet delay log (for CDF plots)           |
| `results/<tag>_flowmon.xml`       | FlowMonitor XML dump                           |
| `plots/ofat_sensitivity.png`      | Tornado chart: parameter impact on L_eff       |
| `plots/bg_load_sweep.png`         | L_eff vs background load per standard          |
| `plots/performer_sweep.png`       | L_eff vs performer count per standard          |
| `plots/summary_table.csv`         | Mean ± 95% CI across seeds per configuration   |

---

## QoS Thresholds (Source: music performance research)

| Threshold | Value   | Meaning                                   |
|-----------|---------|-------------------------------------------|
| Hard      | 10 ms   | Professional ensemble performance limit   |
| Soft      | 20 ms   | Marginal — perceptible, possibly usable   |
| Fail      | > 20 ms | Clearly audible — not viable              |

*Note: No official ITU-T standard defines MIDI latency. Thresholds are derived
from psychoacoustic research on musician timing perception.*

---

## Limitations

The simulation provides an **optimistic lower bound** on real-world latency.
Factors not modelled:
- Multipath fast fading beyond Nakagami-m
- AP firmware heuristics and proprietary scheduling
- OS/driver processing delay (0.1–0.5 ms per packet)
- OS scheduling jitter at the application layer (1–4 ms)
- Clock drift between sender and receiver
- Non-Wi-Fi RF interference (studio equipment, LED dimmers)

---

## Citation / References

- Network MIDI 2.0 UDP specification: MIDI Association (2024)
- ITU-T G.1010 — End-user multimedia QoS categories
- ns-3.47 Wi-Fi module documentation
- Naribole et al., "802.11be MLO in ns-3", WNS3 2020
