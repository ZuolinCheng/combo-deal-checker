# tests/test_benchmarks.py
from benchmarks import BenchmarkLookup


def test_lookup_known_cpu():
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("AMD Ryzen 9 9900X")
    assert result is not None
    assert result.cores > 0
    assert result.single_core_score > 0
    assert result.multi_core_score > 0


def test_lookup_partial_match():
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("Ryzen 9 9900X")
    assert result is not None


def test_lookup_unknown_cpu():
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("Unknown CPU XYZ 9999")
    assert result is None


def test_lookup_cores_threads_format():
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("AMD Ryzen 7 9800X3D")
    assert result is not None
    assert result.threads >= result.cores
