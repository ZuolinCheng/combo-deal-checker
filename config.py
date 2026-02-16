"""Configuration for combo deal checker."""
from dataclasses import dataclass, field


@dataclass
class Config:
    # Budget
    min_budget: float = 500.0
    max_budget: float = 1300.0

    # RAM requirements
    min_ram_gb: int = 32
    ram_type: str = "DDR5"

    # CPU platforms to include
    platforms: list[str] = field(default_factory=lambda: ["AMD", "Intel"])

    # Scraper settings
    headless: bool = True
    min_delay: float = 2.0
    max_delay: float = 5.0
    max_retries: int = 3
    retry_backoff: float = 2.0  # exponential backoff multiplier
    request_timeout: int = 30000  # ms

    # Micro Center location (zip code for pricing)
    microcenter_zip: str = "95054"  # default: Santa Clara, CA

    # Output
    results_dir: str = "results"
    logs_dir: str = "logs"

    # Browser settings
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
