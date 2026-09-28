# Supplier allocation example

This example solves a balanced supplier-to-region transportation problem with the repository linear-programming wrapper. It compares the optimum with a feasible northwest-corner baseline, verifies every capacity and demand constraint independently, renders the allocation matrix, and writes a verified run manifest.

```bash
python -m examples.supplier_allocation.solve
python scripts/run_manifest.py validate examples/supplier_allocation/run-manifest.json \
  --project-root examples/supplier_allocation --verify-files
```

The instance is synthetic and intentionally small enough to audit by hand.
