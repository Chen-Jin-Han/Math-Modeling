import sys
from pathlib import Path

try:
    from _runtime.run_standard_skill import main
except ModuleNotFoundError as exc:
    if exc.name != "_runtime":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from scripts.run_standard_skill import main

if __name__ == "__main__":
    raise SystemExit(main(default_skill="make-model-figures"))
