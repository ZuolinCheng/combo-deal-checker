"""Terminal output using Rich library."""
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.text import Text
from display_names import shorten_cpu, shorten_ram, shorten_motherboard
from models import ComboDeal


def render_deals_table(deals: list[ComboDeal]) -> str:
    """Render deals as a Rich table. Returns string representation."""
    console = Console(record=True, width=200)

    if not deals:
        console.print("[bold red]No deals found matching your criteria.[/bold red]")
        return console.export_text()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    console.print(f"\n[bold]Combo Deal Checker — {now}    Found: {len(deals)}[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Retailer", width=10)
    table.add_column("Type", width=9)
    table.add_column("CPU", width=22)
    table.add_column("Cores", width=8)
    table.add_column("SC", justify="right", width=6)
    table.add_column("MC", justify="right", width=7)
    table.add_column("Motherboard", width=20)
    table.add_column("MB$", justify="right", width=7)
    table.add_column("PCIe5x16", width=10)
    table.add_column("PCIe5M.2", width=9)
    table.add_column("RAM", width=18)
    table.add_column("Speed", width=8)
    table.add_column("Combo$", justify="right", width=8)
    table.add_column("Indiv$", justify="right", width=8)
    table.add_column("Save$", justify="right", width=8)
    table.add_column("URL", width=30)

    for i, deal in enumerate(deals, 1):
        pct = deal.savings_percent()
        if pct > 15:
            style = "green"
        elif pct > 5:
            style = "yellow"
        else:
            style = "white"

        table.add_row(
            str(i),
            deal.retailer,
            deal.combo_type,
            shorten_cpu(deal.cpu_name) or "—",
            deal.cpu_cores or "—",
            str(deal.cpu_sc_score) if deal.cpu_sc_score else "—",
            str(deal.cpu_mc_score) if deal.cpu_mc_score else "—",
            shorten_motherboard(deal.motherboard_name) or "—",
            f"${deal.mb_amazon_price:,.0f}" if deal.mb_amazon_price else "—",
            deal.mb_pcie5_x16 or "—",
            deal.mb_pcie5_m2 or "—",
            shorten_ram(deal.ram_name) or "—",
            f"{deal.ram_speed_mhz}MHz" if deal.ram_speed_mhz else "—",
            f"${deal.combo_price:,.0f}",
            f"${deal.individual_total:,.0f}" if deal.individual_total else "—",
            Text(f"${deal.savings:,.0f}", style=style),
            deal.url[:30] if deal.url else "—",
        )

    console.print(table)

    best = max(deals, key=lambda d: d.savings)
    avg_savings = sum(d.savings for d in deals) / len(deals)
    console.print(f"\n[bold]Best deal:[/bold] {best.retailer} — {shorten_cpu(best.cpu_name) or best.combo_type} combo — saves ${best.savings:,.0f}")
    console.print(f"[bold]Average savings:[/bold] ${avg_savings:,.0f}")

    return console.export_text()
