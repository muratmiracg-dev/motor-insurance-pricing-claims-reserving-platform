# Project Charter

## Decision problem

A fictional Turkish motor own-damage insurer needs to identify underpriced
segments, understand claim-cost drivers, estimate unpaid claim liabilities, and
prioritize a small set of suspicious claims for authorized human review.

## Decisions supported

- Which segments require tariff review?
- Which risk factors affect annual claim frequency and average severity?
- What pure premium is indicated for each policy?
- How do current written premiums compare with the indicated technical premium?
- What paid-loss reserve emerges from Chain Ladder and Bornhuetter-Ferguson?
- Which open claims should investigators inspect first, and why?

## In scope

- Synthetic policy, customer, vehicle, claim, payment, reserve, garage, and triage data
- Exposure-aware frequency modeling
- Positive-cost severity modeling
- Pure-premium and pricing-adequacy analysis
- Written, earned, paid, case-reserve, loss-ratio, and combined-ratio KPIs
- Quarterly paid-loss development triangles
- Chain Ladder and Bornhuetter-Ferguson reserve estimates
- Explainable, human-controlled fraud-triage rules
- Python, SQL, Excel, and Power BI-ready outputs

## Out of scope

- Live policy quotation or claim adjudication
- Real customer or insurer data
- Automatic claim rejection, payment reduction, or adverse action
- Approved actuarial reserves, regulatory submissions, or IFRS 17 accounting
- Production deployment without independent validation and authorization

## Validation design

- Deterministic seed and reproducible data generation
- Underwriting-year time split: 2023–2024 development, 2025 out-of-time test
- Frequency and severity deviance metrics
- Aggregate actual-to-predicted calibration
- Reserve backtest against synthetic ultimate losses
- Precision, recall, and lift for the constrained human-review queue
- Referential-integrity, non-negativity, and human-control unit tests

## Portfolio success criteria

| Area | Acceptance criterion |
| --- | --- |
| Data quality | No orphan policies, claims, or payments; no negative financial amounts |
| Frequency | OOT predicted/actual frequency calibration ratio between 0.85 and 1.15 |
| Pure premium | OOT predicted/actual ultimate calibration ratio between 0.80 and 1.20 |
| Reserving | Portfolio reserve error reported transparently; no negative IBNR |
| Triage | Review queue near configured 5%; precision lift above random review |
| Governance | Zero automatic denials; every reviewed claim receives reason codes |
| Reproducibility | Same seed produces identical core records and metrics |

