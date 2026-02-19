"""Filter logic for combo deals."""
import logging
from models import ComboDeal
from config import Config

logger = logging.getLogger(__name__)


def check_ddr5(deal: ComboDeal) -> bool:
    ram = deal.get_component("ram")
    if not ram:
        return False
    return ram.specs.get("ddr") == 5


def check_ram_capacity(deal: ComboDeal, min_gb: int = 32) -> bool:
    ram = deal.get_component("ram")
    if not ram:
        return False
    return ram.specs.get("capacity_gb", 0) >= min_gb


def check_budget(deal: ComboDeal, min_price: float, max_price: float) -> bool:
    return min_price <= deal.combo_price <= max_price


def check_gpu_compatibility(deal: ComboDeal) -> bool:
    """Check motherboard is compatible with RTX 5000 Ada (PCIe 4.0/5.0 x16).
    All modern AM5/LGA1700/LGA1851 boards qualify."""
    mb = deal.get_component("motherboard")
    if not mb:
        return True
    form_factor = mb.specs.get("form_factor", "").lower()
    if "itx" in form_factor:
        logger.warning(f"Micro-ITX board may have GPU clearance issues: {mb.name}")
    return True


def filter_deals(deals: list[ComboDeal], config: Config) -> list[ComboDeal]:
    filtered = []
    for deal in deals:
        reasons = []
        if not deal.in_stock:
            reasons.append("out of stock")
        if not check_ddr5(deal):
            reasons.append("not DDR5")
        if not check_ram_capacity(deal, min_gb=config.min_ram_gb):
            ram = deal.get_component("ram")
            cap = ram.specs.get("capacity_gb", 0) if ram else 0
            reasons.append(f"RAM {cap}GB < {config.min_ram_gb}GB")
        if not check_budget(deal, config.min_budget, config.max_budget):
            reasons.append(f"price ${deal.combo_price:.0f} outside ${config.min_budget:.0f}-${config.max_budget:.0f}")
        if not check_gpu_compatibility(deal):
            reasons.append("GPU incompatible")

        if reasons:
            logger.debug(f"Filtered out [{deal.retailer}] {deal.combo_type} ${deal.combo_price:.0f} "
                         f"({deal.cpu_name or 'no CPU'}) — {', '.join(reasons)} | {deal.url}")
        else:
            filtered.append(deal)
    filtered.sort(key=lambda d: (-d.savings, -d.cpu_sc_score))
    return filtered
