# Contributing

1. Keep all example records synthetic.
2. Add or update tests for analytical logic changes.
3. Preserve the human-review boundary for fraud triage.
4. Document changes to economic, pricing, or reserving assumptions.
5. Run `PYTHONPATH=src python -m unittest discover -s tests -v` before opening a pull request.

Changes that affect reported metrics must regenerate `artifacts/run_manifest.json`
with the controlled seed and explain any material movement.

