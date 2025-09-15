from __future__ import annotations
import json, os, time, urllib.request
from pathlib import Path
from typing import Dict, Any

def _env_url() -> str:
    url = os.environ.get("OLP_URL")
    if url: return url
    base = os.environ.get("OLP_BASE", "http://127.0.0.1:8088")
    return f"{base.rstrip('/')}/frame"

def post_frame(frame: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(_env_url(),
        data=json.dumps(frame).encode("utf-8"),
        headers={"content-type":"application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        txt = r.read().decode("utf-8","replace")
        try: return json.loads(txt)
        except Exception: return {"ok": False, "raw": txt}

def build_frame(*, claim: str, delta_scale: float = 0.0,
                attrs: Dict[str, Any] | None = None) -> Dict[str, Any]:
    attrs = attrs or {"asset_class":"equity","cadence_pair":"min↔hour"}
    return {
        "stream_id":"reflex",
        "t_logical":int(time.time()),
        "gauge":"sym",
        "units":"confidence:0..1,cost:tokens",
        "nodes":[{"id":"C1","type":"Claim","label":claim,"weight":0.62,"attrs":attrs}],
        "edges":[], "morphs":[],
        "telem":{"delta_scale": float(delta_scale)}
    }

def build_receipt(*, claim: str, because: list[str], but: list[str], so: str,
                  delta_scale: float, threshold: float = 0.03,
                  model: str = "coherence/reflex-loop",
                  attrs: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "claim": claim, "because": because, "but": but, "so": so,
        "telem": {"delta_scale": float(delta_scale)},
        "threshold": float(threshold),
        "model": model, "attrs": attrs or {"cadence":"day"}
    }

def write_receipt_file(receipt: Dict[str, Any], file: str="docs/receipt.latest.json") -> str:
    p = Path(file); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return str(p)
