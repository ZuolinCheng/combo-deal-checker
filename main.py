#!/usr/bin/env python3
"""Combo Deal Checker — main entry point."""
import asyncio
import logging
import sys
import os
from datetime import datetime

from config import Config
from cache import DealCache
from models import ComboDeal
from scrapers.newegg import NeweggScraper
from scrapers.amazon import AmazonScraper
from scrapers.microcenter import MicroCenterScraper
from scrapers.bhphoto import BHPhotoScraper
from scrapers.ram import NeweggRAMScraper, AmazonRAMScraper, MicroCenterRAMScraper, BHPhotoRAMScraper
from benchmarks import BenchmarkLookup
from enrichment import enrich_deals
from price_lookup import AmazonPriceLookup
from filters import filter_deals
from ram_filters import filter_ram_deals
from output.terminal import render_deals_table, render_ram_table
from output.html import render_html_report
from notifications import (
    load_seen_urls, normalize_url, send_discord_notifications,
    send_ram_discord_notifications, send_discord_file, find_expired_deals,
    send_discord_expired_notifications,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join("logs", f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        ),
    ],
)
logger = logging.getLogger(__name__)


def _load_env(path: str = ".env"):
    """Load key=value pairs from .env file into os.environ."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


async def main():
    _load_env()
    config = Config()

    # Parse CLI args
    if "--visible" in sys.argv:
        config.headless = False
    if "--debug" in sys.argv:
        logging.getLogger().setLevel(logging.DEBUG)
    fresh = "--fresh" in sys.argv

    # Initialize cache
    cache = DealCache(cache_dir=config.cache_dir, price_ttl=config.price_cache_ttl)
    if fresh:
        cache.clear()
        logger.info("Running with --fresh: all caches cleared")

    # Ensure output dirs exist
    os.makedirs(config.results_dir, exist_ok=True)
    os.makedirs(config.logs_dir, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Combo Deal Checker — Starting")
    logger.info(f"Budget: ${config.min_budget} - ${config.max_budget}")
    logger.info(f"RAM: {config.ram_type} >= {config.min_ram_gb}GB")
    logger.info("=" * 60)

    # Initialize scrapers
    scrapers = [
        NeweggScraper(config, cache=cache),
        MicroCenterScraper(config),
        AmazonScraper(config),
        BHPhotoScraper(config),
    ]

    # Run all scrapers (sequentially to avoid detection)
    all_deals: list[ComboDeal] = []
    scraper_results = {}

    for scraper in scrapers:
        name = scraper.retailer_name
        logger.info(f"\n--- Scraping {name} ---")
        try:
            deals = await scraper.run()
            all_deals.extend(deals)
            scraper_results[name] = {"status": "ok", "count": len(deals)}
            logger.info(f"{name}: found {len(deals)} deals")
        except Exception as e:
            scraper_results[name] = {"status": "error", "error": str(e)}
            logger.error(f"{name}: failed — {e}")

    logger.info(f"\nTotal raw deals: {len(all_deals)}")

    # Enrich with benchmark scores
    benchmark = BenchmarkLookup()
    all_deals = enrich_deals(all_deals, benchmark)

    # Look up Amazon reference prices for savings calculation
    price_lookup = AmazonPriceLookup(config, cache=cache)
    all_deals = await price_lookup.lookup_prices(all_deals)

    # Filter deals
    filtered = filter_deals(all_deals, config)
    logger.info(f"Deals after filtering: {len(filtered)}")

    # --- Standalone DDR5 RAM Search ---
    logger.info("\n" + "=" * 60)
    logger.info("Standalone DDR5 RAM Search — Starting")
    logger.info("=" * 60)

    ram_scrapers = [
        NeweggRAMScraper(config),
        AmazonRAMScraper(config),
        MicroCenterRAMScraper(config),
        BHPhotoRAMScraper(config),
    ]

    all_ram_deals = []
    ram_seen_urls: set[str] = set()

    for scraper in ram_scrapers:
        name = scraper.retailer_name
        logger.info(f"\n--- RAM: Scraping {name} ---")
        try:
            ram_deals = await scraper.run()
            for deal in ram_deals:
                if deal.url and deal.url not in ram_seen_urls:
                    ram_seen_urls.add(deal.url)
                    all_ram_deals.append(deal)
            scraper_results[f"RAM-{name}"] = {"status": "ok", "count": len(ram_deals)}
            logger.info(f"RAM {name}: found {len(ram_deals)} deals")
        except Exception as e:
            scraper_results[f"RAM-{name}"] = {"status": "error", "error": str(e)}
            logger.error(f"RAM {name}: failed — {e}")

    logger.info(f"Total raw RAM deals: {len(all_ram_deals)}")

    # Look up Amazon reference prices for RAM deals
    all_ram_deals = await price_lookup.lookup_ram_prices(all_ram_deals)

    # Filter RAM deals
    filtered_ram = filter_ram_deals(all_ram_deals)
    logger.info(f"RAM deals after filtering: {len(filtered_ram)}")

    # Determine which deals are new (before marking them as seen)
    seen_urls = load_seen_urls()
    new_urls = {d.url for d in filtered if d.url and normalize_url(d.url) not in seen_urls}
    new_ram_urls = {d.url for d in filtered_ram if d.url and normalize_url(d.url) not in seen_urls}

    # Output
    output = render_deals_table(filtered)
    ram_output = render_ram_table(filtered_ram)
    print(output)
    print(ram_output)

    html_path = render_html_report(
        filtered,
        output_dir=config.results_dir,
        new_urls=new_urls,
        ram_deals=filtered_ram,
        new_ram_urls=new_ram_urls,
    )
    logger.info(f"HTML report saved to: {html_path}")

    # Send Discord notifications for new deals + upload HTML report
    notified = send_discord_notifications(filtered, config.discord_webhook_url)
    if notified:
        logger.info(f"Notified {notified} new deal(s) via Discord")
    ram_notified = send_ram_discord_notifications(filtered_ram, config.discord_webhook_url)
    if ram_notified:
        logger.info(f"Notified {ram_notified} new RAM deal(s) via Discord")

    # Notify about expired deals (OOS or disappeared)
    oos_deals, disappeared_urls = find_expired_deals(
        all_deals, all_ram_deals, seen_urls, scraper_results,
    )
    expired_notified = send_discord_expired_notifications(
        oos_deals, disappeared_urls, config.discord_webhook_url,
    )
    if expired_notified:
        logger.info(f"Notified {expired_notified} expired deal(s) via Discord")

    if config.discord_webhook_url and (filtered or filtered_ram):
        send_discord_file(html_path, config.discord_webhook_url, "Full report attached")

    # Persist cache for next run
    cache.save()
    logger.info("Cache saved")

    # Print scraper status summary
    print("\n--- Scraper Status ---")
    for name, result in scraper_results.items():
        status = result["status"]
        if status == "ok":
            print(f"  {name}: {result['count']} deals")
        else:
            print(f"  {name}: FAILED — {result.get('error', 'unknown')}")


if __name__ == "__main__":
    asyncio.run(main())
