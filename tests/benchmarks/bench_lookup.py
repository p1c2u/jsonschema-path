"""Benchmarks for SchemaPath / SchemaAccessor hot paths.

Focus areas:
- deep traversal without refs
- ref resolution cost (local #/$defs/...)
- membership / keys / iteration on large mappings
- SchemaPath.open() cache-hit behavior (cached resolved)
"""

import argparse
from collections.abc import Iterable
from typing import Any

from jsonschema_path.paths import SchemaPath

try:
    # Prefer module execution: `python -m tests.benchmarks.bench_lookup ...`
    from .bench_utils import BenchmarkResult
    from .bench_utils import add_common_args
    from .bench_utils import results_to_json
    from .bench_utils import run_benchmark
    from .bench_utils import write_json
except ImportError:  # pragma: no cover
    # Allow direct execution: `python tests/benchmarks/bench_lookup.py ...`
    from bench_utils import BenchmarkResult  # type: ignore[no-redef]
    from bench_utils import add_common_args  # type: ignore[no-redef]
    from bench_utils import results_to_json  # type: ignore[no-redef]
    from bench_utils import run_benchmark  # type: ignore[no-redef]
    from bench_utils import write_json  # type: ignore[no-redef]


def _build_deep_tree(depth: int) -> dict[str, Any]:
    node: dict[str, Any] = {"value": 1}
    for i in range(depth - 1, -1, -1):
        node = {f"k{i}": node}
    return node


def _deep_keys(depth: int) -> tuple[str, ...]:
    return tuple(f"k{i}" for i in range(depth))


def _make_deep_path(root: SchemaPath, depth: int) -> SchemaPath:
    p = root
    for k in _deep_keys(depth):
        p = p / k
    return p


def _build_mapping(size: int) -> dict[str, int]:
    return {f"k{i}": i for i in range(size)}


def _schema_with_local_ref(depth: int) -> dict[str, Any]:
    # Root contains an object whose value is a $ref to local $defs.
    target = _build_deep_tree(depth)
    return {
        "$defs": {"Target": target},
        "root": {"$ref": "#/$defs/Target"},
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    add_common_args(parser)
    args = parser.parse_args(list(argv) if argv is not None else None)

    repeats: int = args.repeats
    warmup_loops: int = args.warmup_loops

    results: list[BenchmarkResult] = []

    depth = 25 if not args.quick else 10
    loops_read = 120_000 if not args.quick else 15_000

    # --- Deep traversal without $ref ---
    plain_schema = _build_deep_tree(depth)
    plain_root = SchemaPath.from_dict(plain_schema)
    plain_deep = _make_deep_path(plain_root, depth)

    results.append(
        run_benchmark(
            f"schema.read_value.plain.depth{depth}",
            plain_deep.read_value,
            loops=loops_read,
            repeats=repeats,
            warmup_loops=warmup_loops,
        )
    )

    def open_plain_deep() -> None:
        with plain_deep.open() as _:
            return

    # SchemaPath.open() uses a cached resolved object per-path instance.
    results.append(
        run_benchmark(
            f"schema.open.cache_hit.plain.depth{depth}",
            open_plain_deep,
            loops=loops_read,
            repeats=repeats,
            warmup_loops=warmup_loops,
        )
    )

    # --- Deep traversal with a local $ref ---
    ref_schema = _schema_with_local_ref(depth)
    ref_root = SchemaPath.from_dict(ref_schema)
    ref_deep = _make_deep_path(ref_root / "root", depth)

    results.append(
        run_benchmark(
            f"schema.read_value.local_ref.depth{depth}",
            ref_deep.read_value,
            loops=loops_read,
            repeats=repeats,
            warmup_loops=warmup_loops,
        )
    )

    def open_ref_deep() -> None:
        with ref_deep.open() as _:
            return

    results.append(
        run_benchmark(
            f"schema.open.cache_hit.local_ref.depth{depth}",
            open_ref_deep,
            loops=loops_read,
            repeats=repeats,
            warmup_loops=warmup_loops,
        )
    )

    # --- Large mapping operations (no filesystem I/O) ---
    sizes = [10, 1_000, 50_000] if not args.quick else [10, 1_000]
    for size in sizes:
        mapping = _build_mapping(size)
        p = SchemaPath.from_dict({"root": mapping}) / "root"

        loops_keys = 5_000 if size <= 1_000 else 200
        if args.quick:
            loops_keys = min(loops_keys, 500)

        results.append(
            run_benchmark(
                f"schema.keys.mapping.size{size}",
                p.keys,
                loops=loops_keys,
                repeats=repeats,
                warmup_loops=warmup_loops,
            )
        )

        probe_key = f"k{size - 1}" if size else "k0"
        loops_contains = 40_000 if size <= 1_000 else 2_000
        if args.quick:
            loops_contains = min(loops_contains, 5_000)

        def contains_probe(_p: SchemaPath = p, _key: str = probe_key) -> None:
            _ = _key in _p

        results.append(
            run_benchmark(
                f"schema.contains.mapping.size{size}",
                contains_probe,
                loops=loops_contains,
                repeats=repeats,
                warmup_loops=warmup_loops,
            )
        )

        loops_iter = 500 if size <= 1_000 else 3
        if args.quick:
            loops_iter = min(loops_iter, 50)

        def iter_children(_p: SchemaPath = p) -> None:
            for _ in _p:
                pass

        results.append(
            run_benchmark(
                f"schema.iter_children.mapping.size{size}",
                iter_children,
                loops=loops_iter,
                repeats=repeats,
                warmup_loops=warmup_loops,
            )
        )

    payload = results_to_json(results=results)
    write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
