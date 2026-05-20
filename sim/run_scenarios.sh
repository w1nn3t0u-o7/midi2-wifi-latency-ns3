#!/usr/bin/env bash
# MIDI 2.0 Wi-Fi Latency Simulation - Scenario Runner
# Runs each scenario configuration over multiple RngRun seeds,
# appending all runs to the same CSV so the plotter can compute CIs.

NS3_DIR="${HOME}/ns-allinone-3.47/ns-3.47"
SIM="scratch/midi2-latency-sim.cc"
RESULTS_DIR="${HOME}/Projects/midi2-wifi-latency-ns3/results/"

STANDARDS=("80211ac" "80211ax" "80211be")

# Fixed baseline parameters
BASE_MCS=9
BASE_WIDTH=80
BASE_GI=800
BASE_FREQ=5
BASE_SIMTIME=30s

# Number of independent RNG runs per configuration
# 10 runs gives ~95% CI half-width ≈ 0.6σ; 30 runs ≈ 0.36σ
NUM_RUNS=10

# -----------------------------------------------------------------
# Helper: run one simulation (single RngRun) and append results
# Args: standard, extra_args, output_csv, scenario_label,
#       param_name, param_value, rng_run
# -----------------------------------------------------------------
run_sim() {
    local std="$1"
    local extra_args="$2"
    local out_csv="$3"
    local scenario="$4"
    local param_name="$5"
    local param_value="$6"
    local rng_run="$7"

    local raw
    raw=$(cd "$NS3_DIR" && ./ns3 run "$SIM \
--standard=$std \
--mcs=$BASE_MCS \
--channelWidth=$BASE_WIDTH \
--guardInterval=$BASE_GI \
--frequency=$BASE_FREQ \
--simulationTime=$BASE_SIMTIME \
--RngSeed=1 \
--RngRun=$rng_run \
$extra_args" 2>/dev/null)

    # Parse table rows (skip header lines, grab data rows)
    echo "$raw" | grep -E '^[0-9]+[[:space:]]' | while IFS= read -r line; do
        flow_id=$(echo "$line" | awk '{print $1}')
        src=$(echo "$line" | awk '{print $2}')
        dst=$(echo "$line" | awk '{print $3}')
        tx=$(echo "$line" | awk '{print $4}')
        rx=$(echo "$line" | awk '{print $5}')
        lost=$(echo "$line" | awk '{print $6}')
        lossrate=$(echo "$line" | awk '{print $7}' | tr -d '%')
        delay=$(echo "$line" | awk '{print $8}')
        jitter=$(echo "$line" | awk '{print $9}')
        echo "$scenario,$std,$param_name,$param_value,$rng_run,$flow_id,$src,$dst,$tx,$rx,$lost,$lossrate,$delay,$jitter"
    done >>"$out_csv"
}

# -----------------------------------------------------------------
# SCENARIO 1: Network Capacity — sweep nMidi (1..12), no background
# -----------------------------------------------------------------
echo "=== Scenario 1: Network Capacity ==="
S1_CSV="${RESULTS_DIR}/scenario1_capacity.csv"
echo "scenario,standard,param_name,param_value,rng_run,flow_id,src,dst,txPkts,rxPkts,lost,lossRate_pct,meanDelay_ms,jitter_ms" >"$S1_CSV"

for std in "${STANDARDS[@]}"; do
    for n in 1 2 4 6 8 10 12; do
        for run in $(seq 1 $NUM_RUNS); do
            echo "  [$std] nMidi=$n  run=$run/$NUM_RUNS"
            run_sim "$std" "--nMidi=$n --nBackground=0 --midiModel=onoff --distance=10 --downlink=false" \
                "$S1_CSV" "capacity" "nMidi" "$n" "$run"
        done
    done
done
echo " -> $S1_CSV"

# -----------------------------------------------------------------
# SCENARIO 2: Background Noise — sweep nBackground (0..10), nMidi=5
# -----------------------------------------------------------------
echo "=== Scenario 2: Background Noise ==="
S2_CSV="${RESULTS_DIR}/scenario2_background.csv"
echo "scenario,standard,param_name,param_value,rng_run,flow_id,src,dst,txPkts,rxPkts,lost,lossRate_pct,meanDelay_ms,jitter_ms" >"$S2_CSV"

for std in "${STANDARDS[@]}"; do
    for bg in 0 1 2 3 5 8 10; do
        for run in $(seq 1 $NUM_RUNS); do
            echo "  [$std] nBackground=$bg  run=$run/$NUM_RUNS"
            run_sim "$std" "--nMidi=5 --nBackground=$bg --bgDataRate=2Mbps --midiModel=onoff --distance=10 --downlink=false" \
                "$S2_CSV" "background" "nBackground" "$bg" "$run"
        done
    done
done
echo " -> $S2_CSV"

# -----------------------------------------------------------------
# SCENARIO 3: Distance — sweep distance (1..25m), nMidi=5, nBackground=3
# -----------------------------------------------------------------
echo "=== Scenario 3: Distance ==="
S3_CSV="${RESULTS_DIR}/scenario3_distance.csv"
echo "scenario,standard,param_name,param_value,rng_run,flow_id,src,dst,txPkts,rxPkts,lost,lossRate_pct,meanDelay_ms,jitter_ms" >"$S3_CSV"

for std in "${STANDARDS[@]}"; do
    for dist in 1 5 10 15 20 25; do
        for run in $(seq 1 $NUM_RUNS); do
            echo "  [$std] distance=${dist}m  run=$run/$NUM_RUNS"
            run_sim "$std" "--nMidi=5 --nBackground=3 --distance=$dist --midiModel=onoff --downlink=false" \
                "$S3_CSV" "distance" "distance_m" "$dist" "$run"
        done
    done
done
echo " -> $S3_CSV"

echo ""
echo "All scenarios complete. Results in: $RESULTS_DIR"
ls -lh "$RESULTS_DIR"
