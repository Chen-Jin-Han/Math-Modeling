# Queue risk simulation example

This example chooses the smallest server count that meets waiting-time and rejection-risk targets for a finite-capacity M/M/S/k system. It combines the repository's analytical formula with multiple seeded Monte Carlo replications, preserves rejected candidate designs, reports uncertainty, and records the base seed in `run-manifest.json`.

```bash
python -m examples.queue_risk.solve
python scripts/run_manifest.py validate examples/queue_risk/run-manifest.json \
  --project-root examples/queue_risk --verify-files
```

The scenario is synthetic. Queue assumptions should be tested before transferring the result to a real service system.
