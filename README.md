# stale-quote-windows

Measure **stale-quote windows** between a fast reference price feed and a retail broker feed: how often the broker's displayed quote is behind the market, how long it stays behind, and what share of those windows is still open after a given order delay.

Companion code for the series *Measuring Latency Arbitrage*:
- Part 1: [Recording Two Tick Feeds on One Clock](https://hft-latency-arbitrage.hashnode.dev/recording-two-tick-feeds-on-one-clock)
- Full study: [How Long Do Stale Quotes Last?](https://westernpips.com/latency-arbitrage-data-study.html) · DOI [10.5281/zenodo.23364414](https://doi.org/10.5281/zenodo.23364414)

## What it does

1. **Merges** both feeds into one timeline sorted by arrival time and carries the latest quote of each feed forward (no resampling).
2. **Computes the cross-side gap**, spreads included: `fast bid − broker ask` (buy) and `broker bid − fast ask` (sell).
3. **Checks the data**: crossed or locked quotes, update rate per minute, broker spread.
4. **Finds windows**: opens at the first tick where the gap exceeds the threshold, closes at the first tick where it does not.
5. **Summarises** durations: median, percentiles, share under 20 ms and over 100 ms, share still open after 10–150 ms.

## Quick start

```bash
pip install -r requirements.txt
python make_sample_data.py --minutes 30          # synthetic data to try it
python stale_quote_windows.py sample_fast.csv sample_broker.csv --point 0.01 --threshold 30
```

`make_sample_data.py` generates **invented** data so the code can run anywhere. Its numbers are not the results of the study.

## Your own data

Two CSV files, one tick per row, no header:

```
t_ms,bid,ask
```

`t_ms` is the arrival time at the recording machine in milliseconds. **Both feeds must be timestamped by the same clock**, otherwise you measure clock drift as much as the market. `--point` is the price of one point (0.01 for XAUUSD), `--threshold` is the gap in points that opens a window.

## Limits

- Displayed quotes only: no commission, slippage, swap, markup, rejections or last look. Anything measured this way is a gross upper bound.
- At 1 ms resolution, ticks from both feeds can share a timestamp; treat windows of 1–2 ms as noise.
- A window still open when the recording ends is left out.

## Disclosure

The author works at [Westernpips](https://westernpips.com/alexander-vinsky.html), which develops HFT and latency arbitrage software. This repository contains only the example code from the article, not Westernpips software.

## License

MIT
