"""Minimal benchmark utilities (dependency-free).

Mirrors the lightweight benchmark harness used in the `pathable` repo.
"""

import argparse
import json
import os
import platform
import statistics
import sys
import time
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    loops: int
    repeats: int
    warmup_loops: int
    times_s: tuple[float, ...]

    @property
    def total_s_median(self) -> float:
        return statistics.median(self.times_s)

    @property
    def per_loop_s_median(self) -> float:
        if self.loops <= 0:
            return float("inf")
        return self.total_s_median / self.loops

    @property
    def ops_per_sec_median(self) -> float:
        per = self.per_loop_s_median
        if per <= 0:
            return float("inf")
        return 1.0 / per


def _safe_int_env(name: str) -> int | None:
    value = os.environ.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def default_meta() -> dict[str, Any]:
    return {
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "pythondotorg": platform.python_build(),
        "py_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_ref": os.environ.get("GITHUB_REF"),
        "ci": os.environ.get("CI"),
    }


def run_benchmark(
    name: str,
    func: Callable[[], Any],
    *,
    loops: int,
    repeats: int = 5,
    warmup_loops: int = 1,
) -> BenchmarkResult:
    if loops <= 0:
        raise ValueError("loops must be > 0")
    if repeats <= 0:
        raise ValueError("repeats must be > 0")
    if warmup_loops < 0:
        raise ValueError("warmup_loops must be >= 0")

    for _ in range(warmup_loops):
        for __ in range(loops):
            func()

    times: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        for __ in range(loops):
            func()
        end = time.perf_counter()
        times.append(end - start)

    return BenchmarkResult(
        name=name,
        loops=loops,
        repeats=repeats,
        warmup_loops=warmup_loops,
        times_s=tuple(times),
    )


def results_to_json(
    *,
    results: Iterable[BenchmarkResult],
    meta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "meta": dict(meta or default_meta()),
        "benchmarks": {},
    }

    bench: MutableMapping[str, Any] = out["benchmarks"]
    for r in results:
        bench[r.name] = {
            "loops": r.loops,
            "repeats": r.repeats,
            "warmup_loops": r.warmup_loops,
            "times_s": list(r.times_s),
            "median_total_s": r.total_s_median,
            "median_per_loop_s": r.per_loop_s_median,
            "median_ops_per_sec": r.ops_per_sec_median,
        }

    return out


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        required=True,
        help="Write JSON results to this file.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run fewer iterations for a fast sanity check.",
    )

    repeats_env = (
        _safe_int_env("JSONSCHEMA_PATH_BENCH_REPEATS")
        or _safe_int_env("PATHABLE_BENCH_REPEATS")
        or 5
    )
    warmup_env = (
        _safe_int_env("JSONSCHEMA_PATH_BENCH_WARMUP")
        or _safe_int_env("PATHABLE_BENCH_WARMUP")
        or 1
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=repeats_env,
        help="Number of repeats per scenario (median is reported).",
    )
    parser.add_argument(
        "--warmup-loops",
        type=int,
        default=warmup_env,
        help="Warmup passes before timing.",
    )


def write_json(path: str, payload: Mapping[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
