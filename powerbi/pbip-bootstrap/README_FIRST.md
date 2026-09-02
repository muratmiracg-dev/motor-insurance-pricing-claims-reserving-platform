# PBIP bootstrap

Create the actual PBIP folder with Power BI Desktop here. This repository does
not hand-author undocumented report metadata or claim that an unvalidated PBIX
exists.

1. Enable **Power BI Project (.pbip)**, **PBIR**, and **TMDL** preview features.
2. Create a blank report and save as `MotorInsurance/MotorInsurance.pbip`.
3. Import the tables listed in `../model/model_contract.csv`.
4. Apply the relationship contract, theme, and DAX measures.
5. Build the pages from `../DASHBOARD_SPEC.md`.
6. Keep `**/.pbi/localSettings.json` and `**/.pbi/cache.abf` out of Git.

The expected Desktop-owned structure is:

```text
MotorInsurance/
├── MotorInsurance.pbip
├── MotorInsurance.Report/
│   ├── definition.pbir
│   └── definition/
└── MotorInsurance.SemanticModel/
    ├── definition.pbism
    └── definition/
```
