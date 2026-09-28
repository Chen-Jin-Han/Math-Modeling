# Rule-Pack Consumer: Solving and Validation

Consume the canonical validation-gates configuration from the repository root. Inputs are the decision contract, input hashes, seed, model configuration, solver output, and independent validation output. Outputs are a status-bearing result object, gate report, and run evidence. Solver residuals must be labelled numerical residuals, not model truth error; independent validation must declare whether it shares a decision rule.

Failure conditions: missing units/constraints, unexecuted code, unverifiable results, failed feasibility, or P0 gate failure. These prevent `verified` and block paper generation.
