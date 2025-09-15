from __future__ import annotations
from olp_client import build_frame, post_frame, build_receipt, write_receipt_file

def main():
    claim = "SPY likely up tomorrow"
    delta = 0.028

    frame = build_frame(claim=claim, delta_scale=delta)
    posted = False
    try:
        res = post_frame(frame)
        posted = bool(res and res.get("ok"))
        print("[post]", res)
    except Exception as e:
        print("[post] skipped / failed:", e)

    receipt = build_receipt(
        claim=claim,
        because=["Reflex loop coherence stayed within band","30d minute context"],
        but=[f"Scale drift Δ_scale = {delta:.3f} (min↔hour)"],
        so=("Within 3% tolerance — recheck at close" if delta <= 0.03 else
            "Above 3% — needs explanation"),
        delta_scale=delta
    )
    path = write_receipt_file(receipt)
    print("[ok] wrote", path, "(posted:", posted, ")")

if __name__ == "__main__":
    main()
