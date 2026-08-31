from __future__ import annotations

import argparse
import json
from pathlib import Path
from .runner import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="tp001")
    parser.add_argument("--output", default="artifacts")
    parser.add_argument("--protocol", default="PREREGISTRATION.md")
    parser.add_argument("--replicas", type=int, default=32)
    parser.add_argument("--sizes", default="16,24,32,48")
    parser.add_argument("--families", default="square_bond,square_site,triangular_site")
    parser.add_argument("--seed", type=int, default=20260831)
    args = parser.parse_args()
    summary = run(
        Path(args.output), Path(args.protocol), replicas=args.replicas,
        sizes=[int(x) for x in args.sizes.split(",") if x],
        families=[x for x in args.families.split(",") if x], seed=args.seed,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
