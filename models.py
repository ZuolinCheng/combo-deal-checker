"""Data models for combo deal checker."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Component:
    name: str
    category: str  # "cpu" | "motherboard" | "ram"
    specs: dict = field(default_factory=dict)
    individual_price: float = 0.0


@dataclass
class CPUBenchmark:
    cpu_name: str
    cores: int = 0
    threads: int = 0
    single_core_score: int = 0
    multi_core_score: int = 0


@dataclass
class ComboDeal:
    retailer: str
    combo_type: str  # "CPU+MB+RAM" | "CPU+RAM" | "MB+RAM"
    components: list[Component] = field(default_factory=list)
    combo_price: float = 0.0
    individual_total: float = 0.0
    savings: float = 0.0
    url: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Enriched fields (populated after scraping)
    cpu_name: str = ""
    cpu_cores: str = ""  # "16C/32T"
    cpu_sc_score: int = 0
    cpu_mc_score: int = 0
    motherboard_name: str = ""
    ram_name: str = ""
    ram_speed_mhz: int = 0
    ram_capacity_gb: int = 0

    # Stock availability (False = out of stock, filtered before output)
    in_stock: bool = True

    # Motherboard spec fields (populated from cache/motherboards/*.json)
    mb_amazon_price: float = 0.0
    mb_pcie5_x16: str = ""   # e.g. "1 (CPU)", "2 (1C+1B)"
    mb_pcie5_m2: str = ""    # e.g. "1", "2"

    def get_component(self, category: str) -> Component | None:
        for c in self.components:
            if c.category == category:
                return c
        return None

    def calculate_savings(self):
        self.individual_total = sum(c.individual_price for c in self.components)
        self.savings = self.individual_total - self.combo_price

    def savings_percent(self) -> float:
        if self.individual_total <= 0:
            return 0.0
        return (self.savings / self.individual_total) * 100


@dataclass
class RAMDeal:
    """A standalone DDR5 RAM kit deal from a single retailer."""
    retailer: str
    name: str
    capacity_gb: int = 0
    speed_mhz: int = 0
    ddr_version: int = 5
    price: float = 0.0
    amazon_price: float = 0.0
    savings: float = 0.0  # amazon_price - price (positive = retailer is cheaper)
    url: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
