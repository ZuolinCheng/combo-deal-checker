"""CPU benchmark score lookup using a local database of known scores."""
from models import CPUBenchmark

# PassMark-style scores for common CPUs (approximate, for comparison purposes)
_CPU_DATABASE = [
    # AMD Ryzen 9000 series (AM5)
    ("Ryzen 9 9950X", 16, 32, 4600, 65000),
    ("Ryzen 9 9900X", 12, 24, 4500, 52000),
    ("Ryzen 7 9850X3D", 8, 16, 4700, 37000),
    ("Ryzen 7 9850X", 8, 16, 4500, 34000),
    ("Ryzen 7 9800X3D", 8, 16, 4700, 36000),
    ("Ryzen 7 9700X", 8, 16, 4200, 32000),
    ("Ryzen 5 9600X", 6, 12, 4100, 25000),
    ("Ryzen 5 9600", 6, 12, 3900, 23000),
    # AMD Ryzen 7000 series (AM5)
    ("Ryzen 9 7950X", 16, 32, 4300, 63000),
    ("Ryzen 9 7900X", 12, 24, 4200, 50000),
    ("Ryzen 7 7800X3D", 8, 16, 4400, 33000),
    ("Ryzen 7 7700X", 8, 16, 4000, 30000),
    ("Ryzen 5 7600X", 6, 12, 3900, 23000),
    ("Ryzen 5 7600", 6, 12, 3700, 22000),
    # Intel 15th Gen Arrow Lake (LGA 1851)
    ("Core Ultra 9 285K", 24, 24, 4700, 55000),
    ("Core Ultra 7 265K", 20, 20, 4500, 45000),
    ("Core Ultra 7 265KF", 20, 20, 4500, 45000),
    ("Core Ultra 5 245K", 14, 14, 4300, 33000),
    ("Core Ultra 5 245KF", 14, 14, 4300, 33000),
    # Intel 14th Gen Raptor Lake Refresh (LGA 1700)
    ("Core i9-14900K", 24, 32, 4500, 59000),
    ("Core i9-14900KF", 24, 32, 4500, 59000),
    ("Core i7-14700K", 20, 28, 4300, 47000),
    ("Core i7-14700KF", 20, 28, 4300, 47000),
    ("Core i5-14600K", 14, 20, 4100, 33000),
    ("Core i5-14600KF", 14, 20, 4100, 33000),
    # Intel 13th Gen Raptor Lake (LGA 1700)
    ("Core i9-13900K", 24, 32, 4300, 56000),
    ("Core i9-13900KF", 24, 32, 4300, 56000),
    ("Core i7-13700K", 16, 24, 4100, 40000),
    ("Core i7-13700KF", 16, 24, 4100, 40000),
    ("Core i5-13600K", 14, 20, 3900, 30000),
    ("Core i5-13600KF", 14, 20, 3900, 30000),
    # Intel 12th Gen Alder Lake (LGA 1700)
    ("Core i9-12900K", 16, 24, 3900, 45000),
    ("Core i9-12900KF", 16, 24, 3900, 45000),
    ("Core i7-12700K", 12, 20, 3800, 35000),
    ("Core i7-12700KF", 12, 20, 3800, 35000),
    ("Core i5-12600K", 10, 16, 3700, 27000),
    ("Core i5-12600KF", 10, 16, 3700, 27000),
]


class BenchmarkLookup:
    def __init__(self):
        self._db = []
        for name, cores, threads, sc, mc in _CPU_DATABASE:
            self._db.append(CPUBenchmark(
                cpu_name=name,
                cores=cores,
                threads=threads,
                single_core_score=sc,
                multi_core_score=mc,
            ))

    def get_benchmark(self, cpu_name: str) -> CPUBenchmark | None:
        """Look up benchmark scores by CPU name (fuzzy match).

        Normalizes dashes to spaces so 'i7-14700K' matches 'i7 14700k'.
        """
        cpu_name_norm = cpu_name.lower().replace("-", " ")
        for entry in self._db:
            entry_norm = entry.cpu_name.lower().replace("-", " ")
            if entry_norm in cpu_name_norm or cpu_name_norm in entry_norm:
                return entry
        # Try partial match on key identifiers (e.g. model number)
        for entry in self._db:
            parts = entry.cpu_name.split()
            model = parts[-1] if parts else ""
            model_norm = model.lower().replace("-", " ")
            if model_norm in cpu_name_norm:
                return entry
        return None
