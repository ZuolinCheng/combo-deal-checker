"""Filter logic for standalone RAM deals."""
import logging
from models import RAMDeal

logger = logging.getLogger(__name__)

# Price limits by capacity tier
RAM_PRICE_LIMITS = {
    48: 450.0,
    64: 650.0,
    96: 800.0,
    128: 800.0,
}

VALID_CAPACITIES = {48, 64, 96, 128}


def check_ram_capacity(deal: RAMDeal) -> bool:
    """Capacity must be > 32GB and in the set of valid capacities."""
    return deal.capacity_gb in VALID_CAPACITIES


def check_ram_ddr5(deal: RAMDeal) -> bool:
    """Must be DDR5."""
    return deal.ddr_version == 5


def check_ram_price(deal: RAMDeal) -> bool:
    """Price must be within the limit for its capacity tier."""
    limit = RAM_PRICE_LIMITS.get(deal.capacity_gb)
    if limit is None:
        return False
    return 0 < deal.price <= limit


def filter_ram_deals(deals: list[RAMDeal]) -> list[RAMDeal]:
    """Filter and sort standalone RAM deals.

    Returns deals sorted by savings descending, then speed descending.
    """
    filtered = []
    for deal in deals:
        reasons = []
        if not check_ram_ddr5(deal):
            reasons.append("not DDR5")
        if not check_ram_capacity(deal):
            reasons.append(f"capacity {deal.capacity_gb}GB not in target set")
        if not check_ram_price(deal):
            limit = RAM_PRICE_LIMITS.get(deal.capacity_gb)
            if limit is not None:
                reasons.append(f"price ${deal.price:.0f} exceeds ${limit:.0f} limit for {deal.capacity_gb}GB")
        if reasons:
            logger.debug(
                f"RAM filtered out [{deal.retailer}] {deal.name} ${deal.price:.0f} "
                f"— {', '.join(reasons)}"
            )
        else:
            filtered.append(deal)

    filtered.sort(key=lambda d: (-d.savings, -d.speed_mhz))
    return filtered
