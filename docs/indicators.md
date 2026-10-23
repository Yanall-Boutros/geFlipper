# Indicator notes

> **Unvalidated.** These are AI-generated suggestions, kept as a starting point.
> None has been backtested against real GE data yet. Treat every signal and
> threshold below as a hypothesis.

The notes below assume per-item price and volume history at several
resolutions (5-minute up to daily). Today the backend has only the GE price
dump, one point per Jagex update (about daily). See
[What is implemented](#what-is-implemented) for how the indicators are adapted
to that.

## Indicators

### 1. Volume Profile (VPVR) and volume-at-price

- **Why it might work in OSRS:** GE order books are hidden; you can't see
  pending offers. A volume profile shows where players are buying and selling
  heavily. High Volume Nodes (HVNs) mark "fair value" zones where price
  consolidates, and Low Volume Nodes (LVNs) mark gaps that price moves through
  quickly.
- **Signal:** buy at the bottom of an HVN or near the Value Area Low (VAL).
  Sell at the top edge of the HVN or near the Value Area High (VAH).

### 2. Moving-average envelopes / EMA

- **Why it might work:** high-volume items (Zulrah scales, cannonballs, runes,
  chinchompas) tend to revert to a short intraday average (5- or 10-period EMA).
- **Signal:** buy when price dips below the lower envelope. Sell when it breaks
  the upper envelope, expecting it to fall back toward the EMA.

### 3. RSI / stochastic oscillator

- **Why it might work:** high-tier gear (Scythe, Tumeken's Shadow, Torva) tends
  to get overbought around boss-release announcements and oversold in panic
  selling after updates.
- **Signal:** on 5m–1h data, RSI below 25 together with a volume spike suggests
  panic selling (a buying opportunity). RSI above 75 suggests FOMO buying (a
  time to sell).

### 4. VWAP (volume-weighted average price)

- **Why it might work:** it gives a realistic average fill price because it
  weights each trade by its size.
- **Signal:** if the current instant-buy price is well below VWAP, the item is
  trading at a discount.

## Suggested combinations

### A. High-volume consumables (day flipping)

| | |
| --- | --- |
| **Target items** | Death runes, revenant ether, cannonballs, Zulrah scales, PvM supplies |
| **Indicators** | VPVR + 5/20 EMA envelopes + volume |
| **Timeframe** | 5–15 minute data |
| **Buy** | Slow-buy limit offer at the lower 5-EMA envelope, near a VPVR high-volume node |
| **Volume check** | 5-minute volume should be stable; avoid items whose volume is collapsing unusually |
| **Sell** | Slow-sell limit offer just below the upper envelope or the VPVR high |
| **Margin check** | `sell × (1 − GE tax) − buy > 0` |

### B. High-value gear and update speculation (1–7 day holds)

| | |
| --- | --- |
| **Target items** | PvM weapons and armour (Scythe of Vitur, Masori, Osmumten's fang, Elder maul) |
| **Indicators** | 200 EMA + RSI(14) + VPVR |
| **Timeframe** | 1h–4h and daily data |
| **Buy** | During a panic sell-off, when price reaches a major VPVR support node and 1h RSI drops below 30 |
| **Volume check** | Look for one very large 1-hour volume bar, which suggests merchers are absorbing a liquidation |
| **Sell** | At the next VPVR resistance level, or when 4h RSI crosses above 70 |

## GE tax

The original notes assumed a 1% tax. The GE tax went up to **2%** in May 2025.
Items that sell for under 50 gp are exempt, and the tax per item is capped at
5M gp. Check the current rules on the wiki before relying on these numbers in
margin calculations.

## What is implemented

The backend's indicator engine (see
[`backend/ReadME.md`](../backend/ReadME.md#indicator-engine)) computes these
for every priced item after each Jagex update. Results go in the
`item_indicators` table and are served by `GET /api/v1/items/{id}/indicators`.

| Indicator above | Implemented as | Parameters |
| --- | --- | --- |
| 1. Volume profile | `vp_poc`, `vp_vah`, `vp_val` | Last 30 updates, 24 price buckets, 70% value area |
| 2. EMA / envelopes | `ema_5`, `ema_20`, `ema_200`, `env_upper`, `env_lower` | Envelope ±2% around EMA-5 |
| 3. RSI / stochastic | `rsi_14`; `stoch_k`, `stoch_d` | Wilder RSI(14); %K(14), %D(3) |
| 4. VWAP | `vwap_20`, `vwap_dev_pct` | Last 20 updates |
| Volume checks (combinations A/B) | `rel_volume` | This update's volume ÷ the mean of the previous 20 |

### Differences from the notes

- **Timeframe.** Every period counts Jagex updates, not minutes. EMA-5 is
  about a 5-day average, and EMA-200 needs about 200 updates (roughly 7
  months) of history. The 5–15 minute strategy in combination A needs the
  wiki's `/5m` data, which isn't collected yet.
- **No high/low.** The dump has one price per update, so the stochastic
  oscillator uses the range of recent prices instead of high/low bars.
- **Volume is daily.** `volume` is the dump's traded volume for the day, so
  VWAP and the volume profile are weighted by daily volume.
- **Volume profile summary only.** The engine stores the point of control and
  the value-area high/low. It doesn't store the full histogram or label
  high/low-volume nodes.
- **Warm-up.** Each indicator is NULL until the item has enough priced updates
  (the `samples` column counts them).

### Not built yet

- Buy/sell signals and the combinations above. The engine stores indicator
  values only.
- The margin check with GE tax. It needs separate instant-buy and instant-sell
  prices, from the wiki's `/latest` endpoint.
- Screening across items (for example "every item with RSI below 25").
