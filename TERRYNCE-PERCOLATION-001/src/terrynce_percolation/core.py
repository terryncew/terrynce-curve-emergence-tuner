from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Iterable

KNOWN_PC = {
    "square_bond": 0.5,
    "square_site": 0.59274605079210,
    "triangular_site": 0.5,
}


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


@dataclass(frozen=True)
class Observables:
    load: float
    giant_fraction: float
    component_fraction: float
    susceptibility: float
    spanning: float


def _index(r: int, c: int, n: int) -> int:
    return r * n + c


def _edges(n: int, triangular: bool = False) -> Iterable[tuple[int, int]]:
    for r in range(n):
        for c in range(n):
            here = _index(r, c, n)
            if c + 1 < n:
                yield here, _index(r, c + 1, n)
            if r + 1 < n:
                yield here, _index(r + 1, c, n)
            if triangular and r + 1 < n and c + 1 < n:
                yield here, _index(r + 1, c + 1, n)


def simulate_once(family: str, n: int, p: float, rng: random.Random) -> Observables:
    if family not in KNOWN_PC:
        raise ValueError(f"unknown family: {family}")
    total = n * n
    uf = UnionFind(total)

    if family == "square_bond":
        active = [True] * total
        for a, b in _edges(n):
            if rng.random() < p:
                uf.union(a, b)
        load = p
    else:
        active = [rng.random() < p for _ in range(total)]
        triangular = family == "triangular_site"
        for a, b in _edges(n, triangular=triangular):
            if active[a] and active[b]:
                uf.union(a, b)
        load = sum(active) / total

    members: dict[int, int] = {}
    left_roots, right_roots, top_roots, bottom_roots = set(), set(), set(), set()
    for r in range(n):
        for c in range(n):
            i = _index(r, c, n)
            if not active[i]:
                continue
            root = uf.find(i)
            members[root] = members.get(root, 0) + 1
            if c == 0:
                left_roots.add(root)
            if c == n - 1:
                right_roots.add(root)
            if r == 0:
                top_roots.add(root)
            if r == n - 1:
                bottom_roots.add(root)

    occupied = sum(members.values())
    if occupied == 0:
        return Observables(load, 0.0, 1.0, 0.0, 0.0)
    sizes = sorted(members.values(), reverse=True)
    giant = sizes[0]
    finite = sizes[1:]
    susceptibility = (sum(s * s for s in finite) / sum(finite)) if finite else 0.0
    spanning = float(bool((left_roots & right_roots) or (top_roots & bottom_roots)))
    return Observables(
        load=load,
        giant_fraction=giant / occupied,
        component_fraction=len(sizes) / occupied,
        susceptibility=susceptibility,
        spanning=spanning,
    )


def aggregate(family: str, n: int, p: float, replicas: int, seed: int) -> dict:
    rows = [simulate_once(family, n, p, random.Random(seed + i * 1000003)) for i in range(replicas)]
    def mean(name: str) -> float:
        return sum(getattr(x, name) for x in rows) / replicas
    return {
        "family": family,
        "n": n,
        "p": p,
        "load": mean("load"),
        "giant_fraction": mean("giant_fraction"),
        "component_fraction": mean("component_fraction"),
        "susceptibility": mean("susceptibility"),
        "spanning_probability": mean("spanning"),
    }


def add_terrynce_score(rows: list[dict]) -> list[dict]:
    """Add a frozen, label-free transition score.

    The mapping deliberately excludes known p_c. Load is the realized occupancy/bond
    control. Relief exhaustion is 1 - component_fraction: the degree to which local
    fragmentation capacity has been consumed by mergers. Agreement rewards concordance
    between realized load and merger progress. The transition observable is the
    central finite difference dS/dp, not S itself.
    """
    groups: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["family"], row["n"]), []).append(row)
    out: list[dict] = []
    for key, group in groups.items():
        group = sorted(group, key=lambda r: r["p"])
        for row in group:
            exhaustion = max(0.0, min(1.0, 1.0 - row["component_fraction"]))
            agreement = 1.0 - abs(row["load"] - exhaustion)
            score = row["load"] * exhaustion * max(0.0, agreement)
            item = dict(row)
            item.update({"relief_exhaustion": exhaustion, "agreement": agreement, "terrynce_score": score})
            out.append(item)
    groups2: dict[tuple[str, int], list[dict]] = {}
    for row in out:
        groups2.setdefault((row["family"], row["n"]), []).append(row)
    final: list[dict] = []
    for key, group in groups2.items():
        group = sorted(group, key=lambda r: r["p"])
        for i, row in enumerate(group):
            item = dict(row)
            if 0 < i < len(group) - 1:
                dp = group[i + 1]["p"] - group[i - 1]["p"]
                item["terrynce_gradient"] = (group[i + 1]["terrynce_score"] - group[i - 1]["terrynce_score"]) / dp
                item["giant_gradient"] = (group[i + 1]["giant_fraction"] - group[i - 1]["giant_fraction"]) / dp
            else:
                item["terrynce_gradient"] = math.nan
                item["giant_gradient"] = math.nan
            final.append(item)
    return final


def estimate_pc(rows: list[dict], family: str, n: int, observable: str) -> float:
    candidates = [r for r in rows if r["family"] == family and r["n"] == n and math.isfinite(float(r[observable]))]
    if not candidates:
        raise ValueError("no candidates")
    if observable == "susceptibility":
        return max(candidates, key=lambda r: r[observable])["p"]
    if observable == "spanning_probability":
        return min(candidates, key=lambda r: abs(r[observable] - 0.5))["p"]
    return max(candidates, key=lambda r: r[observable])["p"]


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return math.nan
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else math.nan


def summarize(rows: list[dict], families: list[str], sizes: list[int]) -> dict:
    records = []
    for family in families:
        truth = KNOWN_PC[family]
        for n in sizes:
            estimates = {
                "terrynce": estimate_pc(rows, family, n, "terrynce_gradient"),
                "giant": estimate_pc(rows, family, n, "giant_gradient"),
                "susceptibility": estimate_pc(rows, family, n, "susceptibility"),
                "spanning": estimate_pc(rows, family, n, "spanning_probability"),
            }
            records.append({
                "family": family,
                "n": n,
                "known_pc": truth,
                "estimates": estimates,
                "absolute_error": {k: abs(v - truth) for k, v in estimates.items()},
            })
    t_errors = [r["absolute_error"]["terrynce"] for r in records]
    best_standard = [min(r["absolute_error"][k] for k in ("giant", "susceptibility", "spanning")) for r in records]
    pairs = [(r["terrynce_score"], r["giant_fraction"]) for r in rows]
    corr = pearson([x for x, _ in pairs], [y for _, y in pairs])
    mean_t = sum(t_errors) / len(t_errors)
    mean_best = sum(best_standard) / len(best_standard)
    if mean_t < mean_best and (not math.isfinite(corr) or abs(corr) < 0.98):
        disposition = "ADDITIVE_SIGNAL_CANDIDATE"
    elif math.isfinite(corr) and abs(corr) >= 0.98:
        disposition = "REDUCES_TO_STANDARD_OBSERVABLE"
    else:
        disposition = "NO_ADDITIVE_VALUE"
    return {
        "schema": "terrynce.percolation.summary.v1",
        "records": records,
        "mean_absolute_error": {"terrynce": mean_t, "best_standard_per_case": mean_best},
        "terrynce_vs_giant_pearson": corr,
        "disposition": disposition,
    }
