# Combo Deal Checker

Hardware deal-finding pipeline that scrapes CPU + motherboard + RAM combo deals from multiple retailers, enriches them with benchmark data, filters by user preferences, and generates sortable reports.

## Pipeline

```
Scrapers (4 retailers)  →  Enrichment  →  Filtering  →  Output
```

1. **Scraping** — Playwright-based headless browsers scrape deals from Newegg, Amazon, Micro Center, and B&H Photo. Each scraper extends `BaseScraper` (shared retry logic, delays, browser lifecycle).
2. **Enrichment** — Adds CPU benchmark scores (single/multi-core from local DB of ~49 models), parsed RAM specs (DDR version, capacity, speed), and motherboard names.
3. **Filtering** — DDR5 only, minimum 32GB RAM, $100–$2000 budget, GPU compatibility warnings for Micro-ITX. Sorts by savings then CPU multi-core score.
4. **Output** — Rich terminal table and dark-themed sortable HTML report saved to `results/`.

## Key Files

| File | Role |
|---|---|
| `main.py` | Entry point — orchestrates full pipeline |
| `config.py` | `Config` dataclass — budget, RAM, delays, headless, paths |
| `models.py` | `ComboDeal`, `Component`, `CPUBenchmark` dataclasses |
| `scrapers/base.py` | `BaseScraper` — Playwright setup, retry, delays |
| `scrapers/newegg.py` | Newegg scraper — multi-query, SKU parsing, pagination |
| `scrapers/amazon.py` | Amazon scraper |
| `scrapers/microcenter.py` | Micro Center scraper (zip-code aware) |
| `scrapers/bhphoto.py` | B&H Photo scraper |
| `enrichment.py` | CPU benchmark + RAM spec enrichment |
| `benchmarks.py` | Local CPU benchmark database (AMD Ryzen 9000/7000, Intel Core Ultra/13th-14th gen) |
| `filters.py` | Deal filtering and sorting logic |
| `price_lookup.py` | Amazon individual price lookup for savings calculation |
| `output/terminal.py` | Rich-formatted terminal table |
| `output/html.py` | Sortable HTML report generation |
| `setup_cron.sh` | Cron job — runs every 2 hours |

## Hardware Targets

- **CPUs**: AMD Ryzen 9000/7000 (AM5), Intel Core Ultra 15th gen (LGA1851), Intel Core 13th-14th gen (LGA1700)
- **Motherboards**: X870/X870E/B850/B650/Z890/Z790/Z690 chipsets
- **RAM**: DDR5 exclusively, 32GB minimum
- **Combo types**: CPU+MB+RAM, CPU+RAM, MB+RAM, CPU+MB

## Tech Stack

- Python 3 with `asyncio`
- `playwright` — headless browser automation
- `rich` — terminal output
- `Jinja2` — HTML templating
- `pytest` — test suite

## CLI

```
python main.py              # default headless run
python main.py --visible    # show browser windows
python main.py --debug      # debug-level logging
```

## Conventions

- Scrapers return `list[ComboDeal]`; a failed scraper returns `[]` gracefully
- Duplicate deals filtered by URL (`seen_urls` set)
- Logs go to `logs/run_YYYYMMDD_HHMMSS.log`
- Results go to `results/deals_YYYY-MM-DD_HHMM.html`
