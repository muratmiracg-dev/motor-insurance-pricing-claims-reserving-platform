# Changelog

## Unreleased

- Pricing GLMs now fit with `solver="newton-cholesky", tol=1e-12`. The default L-BFGS stop
  (`tol=1e-4`) left the Poisson and Gamma fits short of the optimum at a point that depended on
  floating-point summation order, so the published coefficients and OOT metrics changed with
  the BLAS kernel of the CI runner (CI failed on some runners with ~1e-5 drift and passed on
  rerun). Converged fits agree within 1e-9 across OpenBLAS Haswell/SkylakeX/Zen/Sandybridge
  kernels and Python 3.11-3.13. Regenerated artifacts: OOT pure-premium calibration
  0.865999 -> 0.866398, increase-review share 33.60% -> 33.59%, frequency calibration
  0.981695 -> 0.982225.
- CI now also rebuilds the Power BI data mart (`scripts/build_powerbi_assets.py`) and compares
  `powerbi/data/` with the committed copy using the same tolerances. Previously the mart was
  never regenerated in CI, so a pipeline change could leave the dashboard data silently stale.
  Python 3.13 added to the CI matrix (pinned requirements reproduce all outputs on 3.11-3.13).
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
