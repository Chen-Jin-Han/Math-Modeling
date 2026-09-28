# Demand forecasting example

This example forecasts the final 12 months of a 36-month demand series without leaking holdout values. It compares a trend-plus-month-effects regression against a seasonal-naive baseline, reports holdout MAE/RMSE/MAPE, produces an SVG diagnostic, and records every input and artifact in `run-manifest.json`.

Run from the repository root:

```bash
python -m examples.demand_forecasting.solve
python scripts/run_manifest.py validate examples/demand_forecasting/run-manifest.json \
  --project-root examples/demand_forecasting --verify-files
```

The data are synthetic and deterministic so the example can be redistributed and regression-tested. This is a workflow demonstration, not a claim about a real market.
