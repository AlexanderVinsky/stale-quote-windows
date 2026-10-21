"""
Generate SYNTHETIC tick data to try the code: a fast feed and a broker feed
that publishes less often and with a delay. The numbers are invented and are
NOT the data from the study.

Usage:
    python make_sample_data.py --minutes 30
    python stale_quote_windows.py sample_fast.csv sample_broker.csv
"""
import argparse

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    # fast feed: ~15 updates per second, random-walk mid price around 4150
    dur = a.minutes * 60_000
    t_fast = np.sort(rng.uniform(0, dur, int(dur / 1000 * 15))).round().astype(int)
    steps = rng.normal(0, 0.05, len(t_fast))
    jumps = rng.random(len(t_fast)) < 0.002          # occasional fast moves
    steps[jumps] += rng.choice([-1, 1], jumps.sum()) * rng.uniform(0.3, 0.8, jumps.sum())
    mid = 4150 + np.cumsum(steps)
    spread_f = 0.06
    np.savetxt("sample_fast.csv", np.c_[t_fast, mid - spread_f / 2, mid + spread_f / 2],
               fmt=["%d", "%.2f", "%.2f"], delimiter=",")

    # broker: ~5 updates per second, shows the fast mid as it was 20-120 ms earlier
    t_brk = np.sort(rng.uniform(0, dur, int(dur / 1000 * 5))).round().astype(int)
    lag = rng.uniform(20, 120, len(t_brk))
    idx = np.searchsorted(t_fast, t_brk - lag, side="right") - 1
    ok = idx >= 0
    t_brk, idx = t_brk[ok], idx[ok]
    spread_b = 0.12
    b_mid = mid[idx]
    np.savetxt("sample_broker.csv", np.c_[t_brk, b_mid - spread_b / 2, b_mid + spread_b / 2],
               fmt=["%d", "%.2f", "%.2f"], delimiter=",")
    print(f"wrote sample_fast.csv ({len(t_fast)} ticks) and sample_broker.csv ({len(t_brk)} ticks)")


if __name__ == "__main__":
    main()
