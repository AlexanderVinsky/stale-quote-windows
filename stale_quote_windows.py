"""
Measure stale-quote windows between a fast reference feed and a broker feed.

Companion code for the series "Measuring Latency Arbitrage":
https://hft-latency-arbitrage.hashnode.dev/recording-two-tick-feeds-on-one-clock

Input: two CSV files with one tick per row and no header:
    t_ms, bid, ask
where t_ms is the arrival time at the recorder in milliseconds, taken from ONE
clock for both feeds.

Usage:
    python stale_quote_windows.py fast.csv broker.csv --point 0.01 --threshold 30
"""
import argparse

import pandas as pd


def load_feed(path: str, src: str) -> pd.DataFrame:
    df = pd.read_csv(path, names=["t_ms", "bid", "ask"])
    df["src"] = src
    return df


def merge_feeds(fast: pd.DataFrame, broker: pd.DataFrame) -> pd.DataFrame:
    """One sorted timeline; every row holds the latest quote of BOTH feeds."""
    ev = (pd.concat([fast, broker], ignore_index=True)
            .sort_values("t_ms", kind="stable")   # stable: keeps file order within one ms
            .reset_index(drop=True))
    is_fast = ev["src"].eq("fast")
    for side in ("bid", "ask"):
        ev["f_" + side] = ev[side].where(is_fast).ffill()
        ev["b_" + side] = ev[side].where(~is_fast).ffill()
    # rows before both feeds have printed at least once are useless
    return ev.dropna(subset=["f_bid", "b_bid"]).reset_index(drop=True)


def add_gap(ev: pd.DataFrame, point: float) -> pd.DataFrame:
    """Cross-side gap in points, spreads included (you buy at ask, sell at bid)."""
    buy_gap = (ev["f_bid"] - ev["b_ask"]) / point    # market bids above broker ask
    sell_gap = (ev["b_bid"] - ev["f_ask"]) / point   # broker bids above market ask
    ev["gap"] = pd.concat([buy_gap, sell_gap], axis=1).max(axis=1)
    ev["side"] = (buy_gap >= sell_gap).map({True: "buy", False: "sell"})
    return ev


def check_data(ev: pd.DataFrame, point: float) -> None:
    """Three checks that catch most bad recordings."""
    for p, name in (("f", "fast"), ("b", "broker")):
        bad = int((ev[p + "_bid"] >= ev[p + "_ask"]).sum())
        print(f"{name:6s} crossed/locked rows: {bad}")
    per_min = ev.groupby([ev["t_ms"] // 60_000, "src"]).size().unstack(fill_value=0)
    print("\nupdates per minute:")
    print(per_min.describe().round(1).to_string())
    spread = (ev["b_ask"] - ev["b_bid"]) / point
    print("\nbroker spread, points:")
    print(spread.describe().round(1).to_string())


def find_windows(ev: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """A window opens at the first tick with gap > threshold and closes at the
    first tick where it is not. A window still open at the end is left out."""
    open_now = ev["gap"] > threshold
    was_open = open_now.shift(fill_value=False)
    starts = ev.loc[open_now & ~was_open, ["t_ms", "side"]].reset_index(drop=True)
    ends = ev.loc[~open_now & was_open, "t_ms"].reset_index(drop=True)
    n = len(ends)
    return pd.DataFrame({
        "start_ms": starts["t_ms"].iloc[:n].to_numpy(),
        "end_ms": ends.to_numpy(),
        "side": starts["side"].iloc[:n].to_numpy(),
    }).assign(duration_ms=lambda d: d["end_ms"] - d["start_ms"])


def summarize(w: pd.DataFrame, hours: float) -> None:
    d = w["duration_ms"]
    print(f"\nwindows: {len(w)}  ({len(w) / hours:.0f} per hour)")
    if len(w) == 0:
        return
    print(f"median {d.median():.0f} ms, 75th pct {d.quantile(.75):.0f} ms, 90th pct {d.quantile(.9):.0f} ms")
    print(f"under 20 ms: {(d < 20).mean():.0%},  over 100 ms: {(d > 100).mean():.0%}")
    for delay in (10, 30, 50, 100, 150):
        print(f"still open after {delay:>3} ms: {(d > delay).mean():.0%}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fast_csv")
    ap.add_argument("broker_csv")
    ap.add_argument("--point", type=float, default=0.01, help="price of one point (XAUUSD: 0.01)")
    ap.add_argument("--threshold", type=float, default=30, help="gap in points that opens a window")
    a = ap.parse_args()

    ev = merge_feeds(load_feed(a.fast_csv, "fast"), load_feed(a.broker_csv, "broker"))
    ev = add_gap(ev, a.point)
    check_data(ev, a.point)
    hours = (ev["t_ms"].iloc[-1] - ev["t_ms"].iloc[0]) / 3_600_000
    summarize(find_windows(ev, a.threshold), hours)


if __name__ == "__main__":
    main()
