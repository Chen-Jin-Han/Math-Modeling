# Rule-Pack Consumer: Review and Release Gates

Inputs: paper source, rendered PDF, result/claim/figure/table/reference registries, dependency analysis, and run manifest. Invoke the canonical validation gates plus the production-document validator. Outputs: rule-ID-bearing review report, PDF preflight report, manual-review checklist, and release decision.

Failure conditions: failed P0 gate, stale hash, missing registered evidence, failed PDF metadata/layout check, or unresolved reference status. Manual visual checks remain manual review and cannot be relabelled as automated passes.
