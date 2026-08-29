from __future__ import annotations

import argparse
import json
from pathlib import Path

from .acquire import acquire
from .canonical import load_csv, validate_cycles
from .calibration import calibrate_real
from .frozen_replay import replay_frozen_real
from .preflight import run_preflight
from .protocol import load_protocol, repo_root
from .replay import replay
from .synthetic import make_fixture


def main() -> None:
    p = argparse.ArgumentParser(prog="tk001")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("acquire")
    a.add_argument("--force", action="store_true")
    sub.add_parser("preflight")
    sub.add_parser("calibrate-real")
    sub.add_parser("replay-frozen-real")
    v = sub.add_parser("validate")
    v.add_argument("csv", type=Path)
    r = sub.add_parser("replay")
    r.add_argument("csv", type=Path)
    r.add_argument("--gnn", type=Path)
    s = sub.add_parser("synthetic")
    s.add_argument("out", type=Path, nargs="?", default=Path("data/processed/synthetic39.csv"))
    args = p.parse_args()
    root = repo_root()

    if args.cmd == "acquire":
        print(json.dumps(acquire(root, force=args.force), indent=2))
    elif args.cmd == "preflight":
        print(json.dumps(run_preflight(root), indent=2))
    elif args.cmd == "calibrate-real":
        print(json.dumps(calibrate_real(root), indent=2))
    elif args.cmd == "replay-frozen-real":
        print(json.dumps(replay_frozen_real(root), indent=2))
    elif args.cmd == "validate":
        proto = load_protocol(root)
        result = validate_cycles(load_csv(args.csv), proto["split"]["n_cycles"])
        print(json.dumps(result, indent=2))
        if result["status"] != "PASS":
            raise SystemExit(2)
    elif args.cmd == "replay":
        print(json.dumps(replay(args.csv, args.gnn, root), indent=2))
    elif args.cmd == "synthetic":
        make_fixture(args.out)
        print(args.out)


if __name__ == "__main__":
    main()
