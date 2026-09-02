# Power BI dashboard package

This folder is the controlled hand-off for a six-page management report. It is
designed to be opened and finalized in Power BI Desktop; it does **not** pretend
that a PBIX binary can be generated or validated on Linux.

## Included assets

- `DASHBOARD_SPEC.md`: page-by-page business questions, visuals, fields, and interactions
- `measures.dax`: one governed KPI layer for all pages
- `theme/motor-insurance-theme.json`: report color and typography theme
- `model/model_contract.csv`: table grain, keys, and source contract
- `model/relationships.csv`: relationship directions and cardinalities
- `data/`: page-ready CSV exports produced from verified analytical artifacts
- `mockups/`: six 16:9 page previews generated from the committed evidence
- `pbip-bootstrap/`: safe Desktop bootstrap files and setup checklist

## Build in Power BI Desktop

1. Run `python scripts/build_powerbi_assets.py` from the repository root.
2. In Desktop, enable the PBIP, PBIR, and TMDL preview features.
3. Create a blank report and save it as a Power BI Project in
   `powerbi/pbip-bootstrap/MotorInsurance`.
4. Import the CSV files from `powerbi/data` with the table names in
   `model/model_contract.csv`.
5. Create the relationships in `model/relationships.csv` using single-direction
   filtering unless the contract explicitly says otherwise.
6. Apply `theme/motor-insurance-theme.json`.
7. Add the measures from `measures.dax` to a dedicated `_Measures` table.
8. Build the six pages using `DASHBOARD_SPEC.md`; compare each page to its mockup.

Power BI Project files are still a Microsoft preview feature. Desktop should
generate the report and semantic-model metadata; do not hand-author undocumented
metadata. The project deliberately keeps the portable, reviewable inputs under
source control and lets Desktop own its cache and generated definitions.

## Governance boundary

All records are synthetic. Pricing and reserving outputs are analytical
indications requiring actuarial validation. The review queue only prioritizes
human investigation; it never denies, reduces, or settles a claim.
