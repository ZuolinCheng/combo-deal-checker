#!/usr/bin/env python3
"""Combo Deal Checker — main entry point."""
import asyncio
import json
import logging
import sys
import os
import time
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
from filters import pre_filter_deals, filter_deals
from ram_filters import pre_filter_ram_deals, filter_ram_deals
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

    # Timing tracker
    timings: list[tuple[str, float]] = []
    pipeline_start = time.monotonic()

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
        t0 = time.monotonic()
        try:
            deals = await scraper.run()
            all_deals.extend(deals)
            scraper_results[name] = {"status": "ok", "count": len(deals)}
            logger.info(f"{name}: found {len(deals)} deals")
        except Exception as e:
            scraper_results[name] = {"status": "error", "error": str(e)}
            logger.error(f"{name}: failed — {e}")
        elapsed = time.monotonic() - t0
        timings.append((f"Scrape {name}", elapsed))
        logger.info(f"{name}: took {elapsed:.1f}s")

    logger.info(f"\nTotal raw deals: {len(all_deals)}")

    # Enrich with benchmark scores
    t0 = time.monotonic()
    benchmark = BenchmarkLookup()
    all_deals = enrich_deals(all_deals, benchmark)
    elapsed = time.monotonic() - t0
    timings.append(("Enrichment", elapsed))

    # Pre-filter before price lookup (skip deals that would fail regardless)
    pre_filtered = pre_filter_deals(all_deals, config)

    # Look up Amazon reference prices for savings calculation (only for pre-filtered)
    t0 = time.monotonic()
    price_lookup = AmazonPriceLookup(config, cache=cache)
    pre_filtered = await price_lookup.lookup_prices(pre_filtered)
    elapsed = time.monotonic() - t0
    timings.append(("Amazon price lookup (combos)", elapsed))
    logger.info(f"Amazon price lookup (combos): took {elapsed:.1f}s")

    # Final filter and sort by savings
    filtered = filter_deals(pre_filtered, config)
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
        t0 = time.monotonic()
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
        elapsed = time.monotonic() - t0
        timings.append((f"Scrape RAM-{name}", elapsed))
        logger.info(f"RAM {name}: took {elapsed:.1f}s")

    logger.info(f"Total raw RAM deals: {len(all_ram_deals)}")

    # Pre-filter RAM before price lookup (skip deals that would fail regardless)
    pre_filtered_ram = pre_filter_ram_deals(all_ram_deals)

    # Look up Amazon reference prices for RAM deals (only for pre-filtered)
    t0 = time.monotonic()
    pre_filtered_ram = await price_lookup.lookup_ram_prices(pre_filtered_ram)
    elapsed = time.monotonic() - t0
    timings.append(("Amazon price lookup (RAM)", elapsed))
    logger.info(f"Amazon price lookup (RAM): took {elapsed:.1f}s")

    # Final filter and sort by savings
    filtered_ram = filter_ram_deals(pre_filtered_ram)
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

    # --- Generate full report (all deals) ---
    html_path = render_html_report(
        filtered,
        output_dir=config.results_dir,
        new_urls=new_urls,
        ram_deals=filtered_ram,
        new_ram_urls=new_ram_urls,
    )
    logger.info(f"HTML report saved to: {html_path}")

    # --- Generate 64GB+ subset report ---
    filtered_64 = [d for d in filtered if d.ram_capacity_gb >= 64]
    filtered_ram_64 = [d for d in filtered_ram if d.capacity_gb >= 64]
    new_urls_64 = {u for u in new_urls if any(d.url == u for d in filtered_64)}
    new_ram_urls_64 = {u for u in new_ram_urls if any(d.url == u for d in filtered_ram_64)}

    html_path_64 = render_html_report(
        filtered_64,
        output_dir=config.results_dir,
        new_urls=new_urls_64,
        ram_deals=filtered_ram_64,
        new_ram_urls=new_ram_urls_64,
        filename_prefix="deals_64gb",
    )
    logger.info(f"64GB+ HTML report saved to: {html_path_64}")
    logger.info(f"64GB+ subset: {len(filtered_64)} combo deals, {len(filtered_ram_64)} RAM deals")

    # Send Discord notifications for new deals (only RAM >= 48GB)
    filtered_48plus = [d for d in filtered if d.ram_capacity_gb and d.ram_capacity_gb >= 48]
    notified = send_discord_notifications(filtered_48plus, config.discord_webhook_url)
    if notified:
        logger.info(f"Notified {notified} new deal(s) via Discord (48GB+ only)")
    filtered_ram_48plus = [d for d in filtered_ram if d.capacity_gb >= 48]
    ram_notified = send_ram_discord_notifications(filtered_ram_48plus, config.discord_webhook_url)
    if ram_notified:
        logger.info(f"Notified {ram_notified} new RAM deal(s) via Discord")

    # Notify about expired deals (OOS or disappeared) — only 48GB+ RAM
    all_deals_48plus = [d for d in all_deals if d.ram_capacity_gb and d.ram_capacity_gb >= 48]
    all_ram_48plus = [d for d in all_ram_deals if d.capacity_gb >= 48]
    oos_deals, disappeared_urls = find_expired_deals(
        all_deals_48plus, all_ram_48plus, seen_urls, scraper_results,
    )
    expired_notified = send_discord_expired_notifications(
        oos_deals, disappeared_urls, config.discord_webhook_url,
    )
    if expired_notified:
        logger.info(f"Notified {expired_notified} expired deal(s) via Discord")

    # Upload 64GB+ report to Discord only if the deal set changed
    if config.discord_webhook_url and (filtered_64 or filtered_ram_64):
        current_64_urls = sorted(
            {d.url for d in filtered_64 if d.url}
            | {d.url for d in filtered_ram_64 if d.url}
        )
        cache_64_file = os.path.join(config.cache_dir, "deals_64gb_urls.json")
        prev_64_urls = []
        if os.path.exists(cache_64_file):
            try:
                with open(cache_64_file, "r") as f:
                    prev_64_urls = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        if current_64_urls != prev_64_urls:
            send_discord_file(html_path_64, config.discord_webhook_url, "64GB+ report attached")
            logger.info("64GB+ report uploaded (deal set changed)")
        else:
            logger.info("64GB+ report unchanged — skipping Discord upload")
        with open(cache_64_file, "w") as f:
            json.dump(current_64_urls, f, indent=2)

    # Persist cache for next run
    cache.save()
    logger.info("Cache saved")

    # Print timing summary
    total_elapsed = time.monotonic() - pipeline_start
    timings.sort(key=lambda x: x[1], reverse=True)
    print("\n--- Timing Breakdown ---")
    for label, secs in timings:
        pct = (secs / total_elapsed * 100) if total_elapsed > 0 else 0
        print(f"  {label:40s} {secs:6.1f}s  ({pct:4.1f}%)")
    print(f"  {'TOTAL':40s} {total_elapsed:6.1f}s")
    logger.info(f"Total pipeline time: {total_elapsed:.1f}s")

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
