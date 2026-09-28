# Production Rule Pack Adapter

The canonical rule definitions are unpacked under `docs/reverse_engineering/skill_rule_pack_v1/`; do not restate or edit rule IDs in this Skill. From the repository root, run the production-pipeline command with `validate-rule-pack` to validate checksums, YAML parsing, unique IDs, mandatory fields, and mapping outputs.

Before `validate`, require registered, hashed results with `verification_status: verified`. A result proposed by a language model is not verified. Before `write`, require every published value to resolve to that registry. Before `visualize`, use `$make-model-figures` and populate each figure's claim, evidence role, and source artifact. Before release, run PDF preflight and preserve `manual_review_required` items rather than converting them into a pass.

The adapter is additive. Existing project-state contracts and specialist Skills remain authoritative where they are stricter or already verified.
