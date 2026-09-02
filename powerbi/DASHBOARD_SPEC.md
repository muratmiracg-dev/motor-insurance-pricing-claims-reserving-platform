# Six-page Power BI dashboard specification

Canvas: 16:9. Persistent slicers: valuation date, underwriting year, region,
vehicle segment, usage type, sales channel, and coverage package. Use the same
KPI definitions from `measures.dax` on every page.

## 1 — Executive Technical Performance

**Decision:** Is the portfolio technically profitable, and where is management
attention required?

| Zone | Visual | Fields / measures | Decision cue |
| --- | --- | --- | --- |
| Header | KPI cards | Earned Premium; Incurred Claims; Loss Ratio; Combined Ratio | Combined ratio above 100% is adverse |
| Left | Clustered bar | Segment; Earned Premium and Incurred Claims | Scale and loss burden |
| Center | Dot plot | Segment; Loss Ratio | Highlight above 75% |
| Right | Decomposition tree | Combined Ratio by region, channel, usage, segment | Identify contributors |
| Footer | Management action table | Segment, Loss Ratio, Combined Ratio, Open Claim Rate | Sort by adverse impact |

Tooltip: exposure years, claim count, frequency, average severity. Selecting a
segment cross-filters the page and drills through to pages 2 and 3.

## 2 — Frequency & Severity Drivers

**Decision:** Is adverse loss cost driven by more claims, larger claims, or both?

| Zone | Visual | Fields / measures | Decision cue |
| --- | --- | --- | --- |
| Header | KPI cards | Claim Frequency; Average Incurred Severity; Claim Count | Current filtered level |
| Left | Scatter | Claim Frequency x Average Severity; size = Incurred Claims; label = segment | Quadrant risk view |
| Center | Small multiples | Dimension/segment; Frequency and Severity indices | Separate frequency/severity drivers |
| Right | Coefficient bar | Feature; multiplicative effect; model selector | Effects above 1 increase expected cost |
| Footer | Detail matrix | Region, vehicle segment, usage; exposure, claims, loss cost | Evidence for pricing review |

Reference lines are portfolio frequency and severity. Coefficients describe model
association, not causal effects.

## 3 — Pricing Adequacy & Scenario Review

**Decision:** Which policies or segments require tariff review, and what is the
premium impact of a controlled rate scenario?

| Zone | Visual | Fields / measures | Decision cue |
| --- | --- | --- | --- |
| Header | KPI cards | Current Written Premium; Indicated Technical Premium; Adequacy Index; Increase Review Share | Adequacy below 1 is adverse |
| Left | Histogram | Pricing Adequacy Index | Distribution around 1.00 |
| Center | Bar | Pricing Action; Policy Count and Premium Gap | Queue size and financial impact |
| Right | What-if cards | Selected Rate Change; Scenario Premium; Scenario Loss Ratio | Non-binding scenario only |
| Footer | Policy review table | Policy ID, segment, current premium, indicated premium, adequacy, action | Exportable review list |

Scenario range: -10% to +25% in 1-point steps. It changes displayed premium and
loss-ratio indications only; it does not automatically change a tariff.

## 4 — Claims Operations & Open Inventory

**Decision:** Where are open-claim backlogs and delayed files accumulating?

| Zone | Visual | Fields / measures | Decision cue |
| --- | --- | --- | --- |
| Header | KPI cards | Open Claim Count; Open Claim Rate; Case Reserve; Average Report Delay | Inventory pressure |
| Left | Bar | Claim Type; Open and Closed Claim Count | Backlog mix |
| Center | Ageing bands | Open claims by days since report | >180-day queue highlighted |
| Right | Garage table | Garage, open files, incurred, average delay | Workload monitoring, not accusation |
| Footer | Claim detail | Claim ID, dates, status, paid, reserve, incurred | Operational drill-through |

Garage signals are workload/context indicators. They must not be interpreted as
proof of misconduct.

## 5 — Reserving & IBNR

**Decision:** What unpaid liability is indicated, how do methods differ, and
which accident periods drive the gap?

| Zone | Visual | Fields / measures | Decision cue |
| --- | --- | --- | --- |
| Header | KPI cards | Latest Paid; Chain Ladder IBNR; BF IBNR; Method Gap | Challenger sensitivity |
| Left | Paid triangle heatmap | Accident quarter x development quarter; cumulative paid | Development maturity |
| Center | Combo chart | Accident quarter; latest paid, CL ultimate, BF ultimate | Period contribution |
| Right | Development-factor line | Development quarter; age-to-age factor | Tail behavior |
| Footer | Backtest table | Accident quarter; true ultimate, estimates, errors | Synthetic validation only |

Synthetic truth is displayed solely for reproducibility/backtesting and would not
exist in a live reserving process.

## 6 — Human Review Queue & Governance

**Decision:** Which claims should authorized investigators review first, and is
the queue operating within its human-control boundary?

| Zone | Visual | Fields / measures | Decision cue |
| --- | --- | --- | --- |
| Header | KPI cards | Review Queue Count; Alert Rate; Precision; Lift; Automated Denials | Automated denials must equal zero |
| Left | Priority bar | Review Priority; Claim Count | Investigator capacity |
| Center | Reason-code bar | Reason Code; flagged claim count | Explain queue composition |
| Right | Score distribution | Triage Score; review status | Threshold transparency |
| Footer | Review queue | Claim ID, priority, score, reason codes, incurred, boundary | Human decision record |

Never expose the synthetic fraud-truth label in an operational view. It belongs
only in offline evaluation evidence.
