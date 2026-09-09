Thoroughly work in progress

insert your auth parameters into `env_template` for connecting to mariadb. Run init_database.py
to create and populate the initial database and tables.

Will add a systemd unit file soon to automate synchronizing the database with outputs from 
`/latest` api endpoint.

To do:
* Add indicators for all tracked items
* Infer how long to hold what volume of items, as well as when to buy and sell that volume

AI Slop recommended indicators:

1. Volume Profile (VPVR) & Volume-at-Price — Highest ReliabilityWhy it works
in OSRS: GE order books are dark (you can't see pending offers), but VPVR reveals
where players are heavily buying and selling. High Volume Nodes (HVNs) show
"fair market value" consolidation zones, while Low Volume Nodes (LVNs) act as
rapid gap areas.  Buy/Sell Signal: Buy at the bottom of an HVN or near the
Value Area Low (VAL). Sell at the top edge of the HVN or near the Value Area
High (VAH).

2. Moving Average Envelopes / Exponential Moving Average (EMA)Why
it works in OSRS: High-volume items (Zulrah scales, Cannonballs, Runes, Chinchompas
) strictly mean-revert around an intraday short-term average (5-EMA or 10-
EMA).Buy/Sell Signal: Buy when price dips below the lower envelope boundary
; sell when it pierces the upper envelope boundary back toward the EMA centerline.

3. Relative Strength Index (RSI) / Stochastic OscillatorWhy it works in OSRS:
High-tier gear (Scythe, Tumeken's Shadow, Torva) frequently gets overbought
during boss release announcements and oversold during post-update panic dumps.
Buy/Sell Signal: On 5m to 1h charts, an RSI below 25 coupled with a volume
spike signals panic selling (instant-buy opportunity). An RSI above 75 signals
FOMO buying (instant-sell/dump opportunity).

4. Volume Weighted Average Price
(VWAP)Why it works in OSRS: Gives an accurate benchmark of the true average
fill price accounting for trade size.  Buy/Sell Signal: If current instant
-buy price is significantly below VWAP, the item is heavily discounted.

Top 2 Indicator Combinations & Timeframe Setup

Combination A: High-Volume / Daily
Consumables FlippingTarget Items: Death runes, Rev ether, Cannonballs, Zulrah
scales, PVM supplies.Combination: VPVR + 5/20 EMA Envelopes + VolumeOptimal
Timeframe: 5-Minute to 15-Minute Charts (Instant/Day Flipping)Strategy Execution
:Buy Price: Place a slow-buy limit offer at the lower boundary of the 5-EMA
Envelope near a High-Volume Node (HVN) on the VPVR.Volume Check: Ensure 5-
minute volume is stable (avoid items experiencing an unnatural volume collapse
).Sell Price: Place a slow-sell limit offer just below the upper boundary of
the Envelope / VPVR High.Margin Calculation: Ensure (Sell Price * 0.99) - Buy
Price > 0 (accounting for the 1% GE tax).

Combination B: High-Value Gear & Update
Speculation (Investment Merching)Target Items: PvM weapons/armour (Scythe of
Vitur, Masori, Osmumten's Fang, Elder Mauls).  Combination: 200 EMA + RSI (
14) + Volume Profile (VPVR)Optimal Timeframe: 1-Hour to 4-Hour / Daily Charts
(Hold duration: 1 to 7 days)Strategy Execution:Buy Price: Wait for a panic
sell-off where price touches a major VPVR Support Node and 1-hour RSI drops
below 30.Volume Check: Look for a massive single 1-hour volume bar (indicating
liquidation/absorption by merchers).Sell Price: Target exit at the next upper
VPVR Resistance level or when 4-hour RSI crosses above 70.
