"""Benchmarks for parsing and SchemaPath construction."""

import argparse
from collections.abc import Iterable
from typing import Any

from pathable import parsers

from jsonschema_path.accessors import SchemaAccessor
from jsonschema_path.paths import SPEC_SEPARATOR
from jsonschema_path.paths import SchemaPath

try:
    # Prefer module execution: `python -m tests.benchmarks.bench_parse ...`
    from .bench_utils import BenchmarkResult
    from .bench_utils import add_common_args
    from .bench_utils import results_to_json
    from .bench_utils import run_benchmark
    from .bench_utils import write_json
except ImportError:  # pragma: no cover
    # Allow direct execution: `python tests/benchmarks/bench_parse.py ...`
    from bench_utils import BenchmarkResult  # type: ignore[no-redef]
    from bench_utils import add_common_args  # type: ignore[no-redef]
    from bench_utils import results_to_json  # type: ignore[no-redef]
    from bench_utils import run_benchmark  # type: ignore[no-redef]
    from bench_utils import write_json  # type: ignore[no-redef]


def _build_args(n: int, *, sep: str) -> list[object]:
    out: list[object] = []
    for i in range(n):
        if i % 11 == 0:
            out.append(".")
        elif i % 11 == 2:
            out.append(i)
        elif i % 11 == 3:
            out.append(f"a{sep}{i}{sep}b")
        else:
            out.append(f"seg{i}")
    return out


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    add_common_args(parser)
    args = parser.parse_args(list(argv) if argv is not None else None)

    repeats: int = args.repeats
    warmup_loops: int = args.warmup_loops

    # Keep accessor construction out of the hot loop.
    accessor = SchemaAccessor.from_schema({"type": "object"})
    sep: str = SPEC_SEPARATOR

    results: list[BenchmarkResult] = []
    sizes = [10, 100, 1_000] if not args.quick else [10, 100]

    for n in sizes:
        inputs = _build_args(n, sep=sep)
        inputs_t = tuple(inputs)

        # Note: older pathable versions (e.g. 0.5.0b2) do not expose
        # BasePath._parse_args publicly. We benchmark `parse_parts` (core of
        # segment splitting/filtering) and then the full SchemaPath constructor.

        loops_parse_parts = 80_000 if n <= 100 else 10_000
        if args.quick:
            loops_parse_parts = min(loops_parse_parts, 10_000)

        def do_parse_parts(_inputs: tuple[Any, ...] = inputs_t) -> None:
            parsers.parse_parts(_inputs, sep=sep)

        results.append(
            run_benchmark(
                f"parse.parse_parts.size{n}",
                do_parse_parts,
                loops=loops_parse_parts,
                repeats=repeats,
                warmup_loops=warmup_loops,
            )
        )

        loops_constructor = 60_000 if n <= 100 else 3_000
        if args.quick:
            loops_constructor = min(loops_constructor, 5_000)

        def do_constructor(_inputs: tuple[Any, ...] = inputs_t) -> None:
            SchemaPath(accessor, *_inputs, separator=sep)

        results.append(
            run_benchmark(
                f"paths.SchemaPath.constructor.size{n}",
                do_constructor,
                loops=loops_constructor,
                repeats=repeats,
                warmup_loops=warmup_loops,
            )
        )

    payload = results_to_json(results=results)
    write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
