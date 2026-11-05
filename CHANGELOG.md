# Changelog

## Unreleased

- Pinned `requirements.txt` to the versions that reproduce the committed artifacts. With the
  previous lower bounds, CI installed scikit-learn 1.9.1, which shifts the Gamma severity GLM
  (coefficients by ~3e-5, OOT predicted ultimate claims by about TRY 3.6k, calibration ratio
  0.865999 -> 0.865987).
- CI now regenerates the pipeline outputs and compares them with the committed `artifacts/`
  (`scripts/compare_artifacts.py`: numbers within relative/absolute 1e-9, text and structure
  exact).
- Fixed the Bornhuetter-Ferguson premium basis. The a-priori ultimate for each accident quarter
  used the full earned premium of policies that *started* in that quarter, while the triangle is
  on an accident-quarter basis and annual policies earn premium over four quarters. Implied loss
  ratios therefore ranged from 0.08 to 5.17 by quarter, and BF understated portfolio ultimate
  losses by 13.08% (68.9% in the valuation quarter). Earned premium is now allocated to calendar
  quarters by days of exposure up to the valuation date. BF IBNR moves from TRY 53.28M to
  TRY 160.00M, and the total error vs synthetic truth from -13.08% to -1.17%. Chain Ladder is
  unchanged.

## 0.2.0 — 2026-09-02

- Added a six-page, decision-led Power BI dashboard specification.
- Added ten page-ready CSV data marts with an explicit grain and relationship contract.
- Added a governed DAX layer for portfolio, pricing, scenario, claims, reserving, triage, and reconciliation KPIs.
- Added a professional Power BI theme and six evidence-based 16:9 page mockups.
- Added a PBIP/PBIR/TMDL Desktop bootstrap checklist without fabricating an unvalidated PBIX binary.
- Removed the synthetic fraud-truth label from the operational Power BI claim table.

## 0.1.0 — 2026-09-02

- Added deterministic 60,000-policy synthetic motor portfolio.
- Added technical KPI and segment-performance layer.
- Added exposure-weighted Poisson frequency and Gamma severity models.
- Added pure-premium indication and pricing-adequacy review.
- Added quarterly Chain Ladder and Bornhuetter-Ferguson reserving.
- Added explainable, human-controlled claim-review triage.
- Added Excel workbench, Power BI DAX starter, PostgreSQL schema, tests, and governance documentation.
