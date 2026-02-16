import os
from output.html import render_html_report, update_index
from models import ComboDeal, Component


def test_render_html_report_creates_file(tmp_path):
    deals = [
        ComboDeal(
            retailer="Newegg",
            combo_type="CPU+MB+RAM",
            combo_price=879.0,
            individual_total=1050.0,
            savings=171.0,
            url="https://newegg.com/deal/123",
            cpu_name="Ryzen 9 9900X",
            cpu_cores="12C/24T",
            cpu_sc_score=4500,
            cpu_mc_score=52000,
            motherboard_name="ASUS X870E",
            ram_name="32GB DDR5-6000",
            ram_speed_mhz=6000,
            ram_capacity_gb=32,
        )
    ]
    filepath = render_html_report(deals, output_dir=str(tmp_path))
    assert os.path.exists(filepath)
    with open(filepath) as f:
        content = f.read()
    assert "Newegg" in content
    assert "879" in content
    assert "sortable" in content.lower() or "sort" in content.lower()


def test_render_html_report_empty_deals(tmp_path):
    filepath = render_html_report([], output_dir=str(tmp_path))
    assert os.path.exists(filepath)


def test_update_index(tmp_path):
    report = tmp_path / "deals_2026-02-15_1400.html"
    report.write_text("<html></html>")
    update_index(str(tmp_path))
    index = tmp_path / "index.html"
    assert index.exists()
    assert "deals_2026-02-15_1400.html" in index.read_text()
