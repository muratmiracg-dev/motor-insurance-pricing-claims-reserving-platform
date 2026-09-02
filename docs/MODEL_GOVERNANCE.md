# Model Governance and Responsible-Use Boundary

## Model inventory

| Component | Method | Permitted use |
| --- | --- | --- |
| Claim frequency | Poisson GLM with exposure weights | Portfolio analysis and tariff research |
| Claim severity | Gamma GLM with claim-count weights | Portfolio analysis and tariff research |
| Technical premium | Frequency × severity with expenses and commission | Indication review only |
| Paid-loss reserve | Chain Ladder | Educational reserve benchmark |
| Expected-loss reserve | Bornhuetter-Ferguson | Educational reserve challenger |
| Claim triage | Transparent weighted rules | Human investigation prioritization only |

## Data boundary

All records and labels are synthetic. The generator excludes gender, ethnicity,
religion, health status, disability, and other protected or unnecessary personal
characteristics. Synthetic fraud truth exists only for evaluation and would not
be available in a real production workflow.

## Human control

No model output constitutes an underwriting decision, policy price, actuarial
reserve, fraud determination, claim rejection, or payment decision. A triage flag
only recommends review. Investigators must gather evidence, document findings,
and follow applicable law and company policy.

## Monitoring

- Monthly frequency and severity calibration
- Pricing-adequacy distribution and extreme-score review
- Segment-level loss-ratio drift
- Reserve backtest and development-factor stability
- Review-queue volume, precision, investigator outcomes, and false positives
- Data-quality, schema, and reconciliation controls

