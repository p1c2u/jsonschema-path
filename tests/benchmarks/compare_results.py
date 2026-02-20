"""Compare two jsonschema-path benchmark JSON results.

Exits non-zero if candidate regresses beyond the configured tolerance.

This mirrors `pathable/tests/benchmarks/compare_results.py`.
"""

import argparse
import json
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import cast


@dataclass(frozen=True)
class ScenarioComparison:
    name: str
    baseline_ops: float
    candidate_ops: float
    ratio: float
    baseline_scenario: str
    candidate_scenario: str


def _canonicalize_scenario_name(name: str) -> str:
    """Return a stable scenario identifier across benchmark renames."""

    aliases: tuple[tuple[str, str], ...] = (
        # jsonschema-path bench_parse canonicalization
        ("parse.parse_parts.", "parse.parts."),
        # If we ever rename the constructor bench, keep it stable.
        ("paths.SchemaPath.constructor.", "paths.SchemaPath.constructor."),
    )

    for prefix, replacement in aliases:
        if name.startswith(prefix):
            return replacement + name[len(prefix) :]
    return name


def _load(path: str) -> Mapping[str, Any]:
    with open(path, encoding="utf-8") as f:
        data_any = json.load(f)
    if not isinstance(data_any, dict):
        raise ValueError("Invalid report: expected top-level JSON object")
    return cast(dict[str, Any], data_any)


def _extract_ops(report: Mapping[str, Any]) -> dict[str, float]:
    benchmarks = report.get("benchmarks")
    if not isinstance(benchmarks, dict):
        raise ValueError("Invalid report: missing 'benchmarks' dict")

    benchmarks_d = cast(dict[str, Any], benchmarks)

    out: dict[str, float] = {}
    for scenario_name, payload in benchmarks_d.items():
        if not isinstance(payload, dict):
            continue
        payload_d = cast(dict[str, Any], payload)
        ops_any = payload_d.get("median_ops_per_sec")
        ops = ops_any if isinstance(ops_any, (int, float)) else None
        if ops is not None:
            out[scenario_name] = float(ops)
    return out


def compare(
    *,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    tolerance: float,
) -> tuple[list[ScenarioComparison], list[ScenarioComparison]]:
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")

    b_raw = _extract_ops(baseline)
    c_raw = _extract_ops(candidate)

    b: dict[str, tuple[str, float]] = {}
    c: dict[str, tuple[str, float]] = {}

    for scenario_name, ops in b_raw.items():
        canon = _canonicalize_scenario_name(scenario_name)
        b.setdefault(canon, (scenario_name, ops))

    for scenario_name, ops in c_raw.items():
        canon = _canonicalize_scenario_name(scenario_name)
        c.setdefault(canon, (scenario_name, ops))

    comparisons: list[ScenarioComparison] = []
    for canon_name in sorted(set(b) & set(c)):
        b_name, bops = b[canon_name]
        c_name, cops = c[canon_name]
        ratio = cops / bops if bops > 0 else float("inf")
        comparisons.append(
            ScenarioComparison(
                name=canon_name,
                baseline_ops=bops,
                candidate_ops=cops,
                ratio=ratio,
                baseline_scenario=b_name,
                candidate_scenario=c_name,
            )
        )

    # Regression if candidate is slower by more than tolerance:
    # candidate_ops < baseline_ops * (1 - tolerance)
    floor_ratio = 1.0 - tolerance
    regressions = [x for x in comparisons if x.ratio < floor_ratio]
    return comparisons, regressions


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.20,
        help="Allowed slowdown (e.g. 0.20 means 20% slower allowed).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    baseline = _load(args.baseline)
    candidate = _load(args.candidate)

    comparisons, regressions = compare(
        baseline=baseline,
        candidate=candidate,
        tolerance=args.tolerance,
    )

    print("scenario\tbaseline_ops/s\tcandidate_ops/s\tratio")
    for c in comparisons:
        print(
            f"{c.name}\t{c.baseline_ops:.2f}\t{c.candidate_ops:.2f}\t{c.ratio:.3f}"
        )

    if regressions:
        print("\nREGRESSIONS:")
        for r in regressions:
            print(
                f"- {r.name}: {r.ratio:.3f}x (baseline {r.baseline_ops:.2f} ops/s, candidate {r.candidate_ops:.2f} ops/s)"
            )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
