# Reduce Amazon Price Lookup Time

**Date:** 2026-02-26
**Problem:** Amazon price lookups consume ~28 min per run (1698s of a 2959s pipeline)

## Root Cause

Price lookups happen before filtering. Most looked-up deals get thrown away:
- Combo deals: 126 component lookups → 61 survive filtering (40% waste)
- RAM deals: ~150 product lookups → 4 survive filtering (98% waste)

## Solution

Two changes:

### 1. Pre-filter before price lookup

Move non-price-dependent filters before the Amazon lookup step:

**Combo deals:** check `in_stock`, `check_ddr5`, `check_ram_capacity`, `check_budget`
**RAM deals:** check `check_ram_ddr5`, `check_ram_capacity`, `check_ram_price`

None of these require Amazon prices. After pre-filtering, only surviving deals get priced.

Pipeline changes from:
```
scrape → enrich → price lookup → filter → sort
```
to:
```
scrape → enrich → pre-filter → price lookup → final sort
```

Keep unfiltered `all_deals` / `all_ram_deals` for expired-deal notifications.

### 2. Extend cache TTL from 8h to 24h

Hardware reference prices don't shift meaningfully within a day.
Prevents redundant lookups across hourly cron runs.

## Expected Impact

| Phase | Before | After |
|---|---|---|
| Amazon lookup (combos) | 696s (126 components) | ~380s (~70 components) |
| Amazon lookup (RAM) | 1002s (~150 products) | ~30s (~5 products) |
| Total pipeline | 2959s (49 min) | ~1670s (28 min) |

## Files Changed

- `main.py` — add pre-filter steps
- `config.py` — change `price_cache_ttl` to 86400
- `filters.py` — extract `pre_filter_deals()` function
- `ram_filters.py` — extract `pre_filter_ram_deals()` function
