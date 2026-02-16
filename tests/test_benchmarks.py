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


# --- Bug #7: Dash-vs-space normalization ---
def test_lookup_space_instead_of_dash():
    """MicroCenter scrapes 'intel core i7 14700k' (spaces) but DB has 'Core i7-14700K' (dash)."""
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("intel core i7 14700k")
    assert result is not None
    assert result.cores > 0


def test_lookup_space_instead_of_dash_i9():
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("intel core i9 14900k")
    assert result is not None


def test_lookup_space_instead_of_dash_i5():
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("intel core i5 13600k")
    assert result is not None


# --- Bug #6: Missing CPUs ---
def test_lookup_9850x3d():
    """AMD Ryzen 7 9850X3D is a common combo CPU and must be in the DB."""
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("AMD Ryzen 7 9850X3D")
    assert result is not None
    assert result.cores == 8


def test_lookup_265kf():
    """Intel Core Ultra 7 265KF must be in the DB."""
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("Intel Core Ultra 7 265KF")
    assert result is not None


def test_lookup_12900k():
    """Intel Core i9-12900K must be in the DB."""
    lookup = BenchmarkLookup()
    result = lookup.get_benchmark("Intel Core i9-12900K")
    assert result is not None
