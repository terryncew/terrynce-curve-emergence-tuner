#!/usr/bin/env python3
"""
Emergence Guard – Public Interface
MIT License   •   github.com/terryncew/emergence-guard

▸ What’s PUBLIC here?
    – monitoring loop
    – logging, CLI, JSON logging, status reports
    – a *toy fallback kernel* so the demo still runs out-of-the-box

▸ What stays PRIVATE?
    – the real Terrynce Curve κ/ε computation
      shipped only as a compiled plug-in (WASM / .so / .pyd)

Drop your compiled kernel in the same folder as:
    emergence_kernel.{so|pyd|wasm}
and the guard will auto-load it.  No source = no IP leak.
"""

import importlib
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

# ──────────────────────────────────────────────────────────────────────────────
#  1.  SAFE DEFAULTS & LOGGING
# ──────────────────────────────────────────────────────────────────────────────
KAPPA_THRESHOLD   = 0.80
EPSILON_THRESHOLD = 0.70
LOG_LEVEL         = "INFO"         # or read from ENV

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s  %(levelname)-8s  %(message)s"
)
log = logging.getLogger("EmergenceGuard")

# ──────────────────────────────────────────────────────────────────────────────
#  2.  KERNEL LOADER  (tries to import your compiled plugin)
# ──────────────────────────────────────────────────────────────────────────────
def _load_private_kernel():
    """
    Looks for emergence_kernel.* (so/pyd/wasm).
    If found: returns kernel.compute_kappa, kernel.compute_epsilon
    Else:     returns fallback toy math  (keeps the demo alive)
    """
    try:
        spec = importlib.util.find_spec("emergence_kernel")
        if spec is None:
            raise ImportError
        kernel = importlib.import_module("emergence_kernel")     # compiled
        log.info("🔒 Loaded private kernel: emergence_kernel")
        return kernel.compute_kappa, kernel.compute_epsilon
    except ImportError:
        log.warning("⚠️  Private kernel not found – using fallback toy math")
        return _fallback_kappa, _fallback_epsilon


def _fallback_kappa(signals: Dict[str, float]) -> float:
    """Toy stress metric – fine for demo, not production."""
    return min(1.0,
               0.3 * signals["cpu_load"] +
               0.3 * signals["memory_usage"] +
               0.2 * signals["network_io"] +
               0.2 * signals["error_rate"])


def _fallback_epsilon(signals: Dict[str, float]) -> float:
    """Toy entropy metric – fine for demo, not production."""
    return min(1.0,
               0.4 * signals["response_variance"] +
               0.3 * signals["token_entropy"] +
               0.2 * signals["pattern_deviation"] +
               0.1 * signals["recursion_depth"])


compute_kappa, compute_epsilon = _load_private_kernel()

# ──────────────────────────────────────────────────────────────────────────────
#  3.  DATACLASS SNAPSHOT
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Snapshot:
    kappa: float
    epsilon: float
    status: str
    timestamp: datetime
    raw: Dict[str, float]


# ──────────────────────────────────────────────────────────────────────────────
#  4.  SENSE ENVIRONMENT  (keep simple; swap with real metrics in prod)
# ──────────────────────────────────────────────────────────────────────────────
def sense_environment() -> Dict[str, float]:
    """Simulated signals; replace with real monitoring hooks."""
    return {
        "cpu_load":           random.uniform(0, 1),
        "memory_usage":       random.uniform(0, 1),
        "network_io":         random.uniform(0, 1),
        "error_rate":         random.uniform(0, 0.3),
        "response_variance":  random.uniform(0, 1),
        "token_entropy":      random.uniform(0, 1),
        "pattern_deviation":  random.uniform(0, 0.5),
        "recursion_depth":    random.uniform(0, 0.8),
    }


# ──────────────────────────────────────────────────────────────────────────────
#  5.  MAIN LOOP
# ──────────────────────────────────────────────────────────────────────────────
def evaluate(kappa: float, epsilon: float) -> str:
    if kappa > KAPPA_THRESHOLD:
        return "CRITICAL – HIGH STRESS"
    if epsilon > EPSILON_THRESHOLD:
        return "CRITICAL – HIGH ENTROPY"
    if kappa > 0.6 or epsilon > 0.5:
        return "WARNING – ELEVATED"
    return "SAFE"


def guard_loop(interval: float = 2.0):
    history: list[Snapshot] = []
    log.info("🛡️  Emergence Guard started")
    log.info(f"Thresholds → κ≤{KAPPA_THRESHOLD}, ε≤{EPSILON_THRESHOLD}")

    try:
        while True:
            signals = sense_environment()
            kappa   = round(compute_kappa(signals),   3)
            epsilon = round(compute_epsilon(signals), 3)
            status  = evaluate(kappa, epsilon)

            snap = Snapshot(kappa, epsilon, status, datetime.utcnow(), signals)
            history.append(snap)
            history[-1000:]  # keep last 1 000

            log.info(f"κ={kappa:.3f}, ε={epsilon:.3f}  →  {status}")

            if status.startswith("CRITICAL"):
                _emergency_shutdown(snap)
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        log.info("👋  User requested stop")


# ──────────────────────────────────────────────────────────────────────────────
#  6.  EMERGENCY HANDLER  (just logs + JSON dump for demo)
# ──────────────────────────────────────────────────────────────────────────────
def _emergency_shutdown(snap: Snapshot):
    log.critical("🚨 EMERGENCY SHUTDOWN triggered")
    dump = {
        "timestamp": snap.timestamp.isoformat(),
        "kappa": snap.kappa,
        "epsilon": snap.epsilon,
        "status": snap.status,
        "signals": snap.raw,
    }
    fname = f"emergency_{int(time.time())}.json"
    Path(fname).write_text(json.dumps(dump, indent=2))
    log.critical(f"Snapshot saved → {fname}")


# ──────────────────────────────────────────────────────────────────────────────
#  7.  CLI ENTRY
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    guard_loop()
