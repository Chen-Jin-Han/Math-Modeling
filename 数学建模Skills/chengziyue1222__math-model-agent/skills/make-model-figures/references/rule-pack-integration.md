# Rule-Pack Consumer: Figure Grammar

Read canonical `04_figure_grammar.yaml` at the repository root. Inputs: problem signals, verified result artifacts, and claim registry. Outputs: figure plan, figure registry, vector master, high-resolution proof, and audit metadata. The grammar chooses a recommendation only when its signal matches; it does not create decorative figures.

Failure conditions: missing claim/evidence role/source, unspecified axis units, unreadable final size, or a claim unsupported by data. Emit a failed figure audit rather than a formal figure.
