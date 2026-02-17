# Caching Layer Design

## Problem
The pipeline is slow because every run launches Playwright browsers for 4 retailers (sequentially, with 2-5s delays per page) and then another browser for Amazon price lookups per component.

## Solution: Three-tier JSON Cache

Three independent JSON files in `cache/`:

| File | Key | Value | TTL |
|---|---|---|---|
| `amazon_prices.json` | Component name | `{price, timestamp}` | 8 hours |
| `deal_details.json` | Deal URL | `{components, combo_type, cpu_name, ram_specs}` | Forever |
| `deal_prices.json` | Deal URL | `{combo_price, timestamp}` | Per-run (always fresh) |

### Behavior
1. **Scraping** — Listing pages are always crawled for current combo prices. Detail page visits are skipped when `deal_details.json` has the URL cached.
2. **Amazon price lookup** — Components with cached prices younger than 8h are skipped. If all are cached, no browser is launched.
3. **`--fresh` flag** — Ignores all caches but writes fresh data back for next run.

## New File: `cache.py`

`DealCache` class with:
- `load_amazon_price(name) -> float | None`
- `save_amazon_price(name, price)`
- `load_deal_detail(url) -> dict | None`
- `save_deal_detail(url, detail_dict)`
- `clear()`

## Changes to Existing Files

| File | Change |
|---|---|
| `config.py` | Add `cache_dir`, `price_cache_ttl` |
| `main.py` | Parse `--fresh`, create `DealCache`, pass to scrapers/price_lookup |
| `scrapers/base.py` | Accept optional `DealCache` |
| `scrapers/newegg.py` | Check/save deal detail cache |
| `price_lookup.py` | Check/save Amazon price cache |
