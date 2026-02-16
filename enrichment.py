"""Enrich combo deals with benchmark scores and parsed specs."""
from models import ComboDeal
from benchmarks import BenchmarkLookup


def enrich_deals(deals: list[ComboDeal], benchmark: BenchmarkLookup) -> list[ComboDeal]:
    for deal in deals:
        _enrich_cpu(deal, benchmark)
        _enrich_ram(deal)
        _enrich_motherboard(deal)
    return deals


def _enrich_cpu(deal: ComboDeal, benchmark: BenchmarkLookup):
    cpu = deal.get_component("cpu")
    if not cpu:
        return
    deal.cpu_name = cpu.name
    result = benchmark.get_benchmark(cpu.name)
    if result:
        deal.cpu_sc_score = result.single_core_score
        deal.cpu_mc_score = result.multi_core_score
        deal.cpu_cores = f"{result.cores}C/{result.threads}T"


def _enrich_ram(deal: ComboDeal):
    ram = deal.get_component("ram")
    if not ram:
        return
    deal.ram_name = ram.name
    deal.ram_speed_mhz = ram.specs.get("speed_mhz", 0)
    deal.ram_capacity_gb = ram.specs.get("capacity_gb", 0)


def _enrich_motherboard(deal: ComboDeal):
    mb = deal.get_component("motherboard")
    if not mb:
        return
    deal.motherboard_name = mb.name
