# Indicator notes

> **Unvalidated.** These are AI-generated suggestions, kept as a starting point.
> None has been backtested against real GE data yet. Treat every signal and
> threshold below as a hypothesis.

The indicators need per-item price and volume history at several resolutions,
which is what the planned background collectors will gather (see
[`backend/ReadME.md`](../backend/ReadME.md#background-data-collection-planned)).

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
