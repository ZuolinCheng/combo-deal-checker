"""HTML report output with sortable table and dark theme."""

import os
import glob
from datetime import datetime

from jinja2 import Template

from display_names import shorten_cpu, shorten_ram, shorten_motherboard
from models import ComboDeal


HTML_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Combo Deal Report - {{ generated_at }}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding: 20px;
  }
  h1 { color: #00d4ff; margin-bottom: 10px; }
  .summary {
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 15px 20px;
    margin-bottom: 20px;
    display: flex;
    gap: 30px;
    flex-wrap: wrap;
  }
  .summary .stat {
    display: flex;
    flex-direction: column;
  }
  .summary .stat .label {
    font-size: 0.8em;
    color: #888;
    text-transform: uppercase;
  }
  .summary .stat .value {
    font-size: 1.3em;
    font-weight: bold;
    color: #00d4ff;
  }
  .meta {
    color: #666;
    font-size: 0.85em;
    margin-bottom: 15px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    background: #16213e;
    border-radius: 8px;
    overflow: hidden;
  }
  th {
    background: #0f3460;
    color: #00d4ff;
    padding: 10px 8px;
    text-align: left;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
    position: relative;
  }
  th:hover { background: #1a4a8a; }
  th.sortable::after { content: ' \\2195'; font-size: 0.7em; opacity: 0.5; }
  td {
    padding: 8px;
    border-bottom: 1px solid #1a1a2e;
  }
  tr:hover { background: #1a2a4e; }
  tr.green td { background: rgba(0, 200, 83, 0.15); }
  tr.yellow td { background: rgba(255, 193, 7, 0.15); }
  a { color: #00d4ff; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .no-deals {
    text-align: center;
    padding: 40px;
    color: #666;
    font-size: 1.2em;
  }
</style>
</head>
<body>
<h1>Combo Deal Checker Report</h1>
<div class="meta">Generated: {{ generated_at }} | Total deals: {{ deals|length }}</div>

{% if deals %}
<div class="summary">
  <div class="stat">
    <span class="label">Best Savings</span>
    <span class="value">${{ "%.2f"|format(best_savings) }}</span>
  </div>
  <div class="stat">
    <span class="label">Average Savings</span>
    <span class="value">${{ "%.2f"|format(avg_savings) }}</span>
  </div>
  <div class="stat">
    <span class="label">Best Deal</span>
    <span class="value">{{ best_deal_name }}</span>
  </div>
</div>
{% endif %}

{% if deals %}
<table id="dealsTable">
<thead>
<tr>
  <th class="sortable" onclick="sortTable(0)">#</th>
  <th class="sortable" onclick="sortTable(1)">Retailer</th>
  <th class="sortable" onclick="sortTable(2)">Type</th>
  <th class="sortable" onclick="sortTable(3)">CPU</th>
  <th class="sortable" onclick="sortTable(4)">Cores</th>
  <th class="sortable" onclick="sortTable(5)">SC</th>
  <th class="sortable" onclick="sortTable(6)">MC</th>
  <th class="sortable" onclick="sortTable(7)">Motherboard</th>
  <th class="sortable" onclick="sortTable(8)">MB$</th>
  <th class="sortable" onclick="sortTable(9)">PCIe5 x16</th>
  <th class="sortable" onclick="sortTable(10)">PCIe5 M.2</th>
  <th class="sortable" onclick="sortTable(11)">RAM</th>
  <th class="sortable" onclick="sortTable(12)">Speed</th>
  <th class="sortable" onclick="sortTable(13)">Combo$</th>
  <th class="sortable" onclick="sortTable(14)">Indiv$</th>
  <th class="sortable" onclick="sortTable(15)">Save$</th>
  <th>URL</th>
</tr>
</thead>
<tbody>
{% for deal in deals %}
<tr class="{{ deal.row_class }}">
  <td>{{ loop.index }}</td>
  <td>{{ deal.retailer }}</td>
  <td>{{ deal.combo_type }}</td>
  <td>{{ deal.display_cpu }}</td>
  <td>{{ deal.cpu_cores }}</td>
  <td>{{ deal.cpu_sc_score }}</td>
  <td>{{ deal.cpu_mc_score }}</td>
  <td>{{ deal.display_mb }}</td>
  <td>{{ "$%.2f"|format(deal.mb_amazon_price) if deal.mb_amazon_price else "—" }}</td>
  <td>{{ deal.mb_pcie5_x16 or "—" }}</td>
  <td>{{ deal.mb_pcie5_m2 or "—" }}</td>
  <td>{{ deal.display_ram }}</td>
  <td>{{ deal.ram_speed_mhz }}</td>
  <td>${{ "%.2f"|format(deal.combo_price) }}</td>
  <td>${{ "%.2f"|format(deal.individual_total) }}</td>
  <td>${{ "%.2f"|format(deal.savings) }}</td>
  <td><a href="{{ deal.url }}" target="_blank">Link</a></td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
<div class="no-deals">No deals found.</div>
{% endif %}

<script>
function sortTable(colIndex) {
  var table = document.getElementById("dealsTable");
  var tbody = table.querySelector("tbody");
  var rows = Array.from(tbody.querySelectorAll("tr"));
  var ascending = table.dataset.sortCol === String(colIndex)
    ? table.dataset.sortDir !== "asc"
    : true;

  rows.sort(function(a, b) {
    var aText = a.cells[colIndex].textContent.trim().replace(/[$,]/g, "");
    var bText = b.cells[colIndex].textContent.trim().replace(/[$,]/g, "");
    var aNum = parseFloat(aText);
    var bNum = parseFloat(bText);
    if (!isNaN(aNum) && !isNaN(bNum)) {
      return ascending ? aNum - bNum : bNum - aNum;
    }
    return ascending
      ? aText.localeCompare(bText)
      : bText.localeCompare(aText);
  });

  rows.forEach(function(row) { tbody.appendChild(row); });
  table.dataset.sortCol = String(colIndex);
  table.dataset.sortDir = ascending ? "asc" : "desc";
}
</script>
</body>
</html>
""")


INDEX_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Combo Deal Reports Index</title>
<style>
  body {
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding: 20px;
  }
  h1 { color: #00d4ff; margin-bottom: 20px; }
  ul { list-style: none; padding: 0; }
  li {
    padding: 8px 0;
    border-bottom: 1px solid #0f3460;
  }
  a { color: #00d4ff; text-decoration: none; font-size: 1.1em; }
  a:hover { text-decoration: underline; }
</style>
</head>
<body>
<h1>Combo Deal Reports</h1>
<ul>
{% for report in reports %}
  <li><a href="{{ report }}">{{ report }}</a></li>
{% endfor %}
</ul>
{% if not reports %}
<p>No reports found.</p>
{% endif %}
</body>
</html>
""")


def _assign_display_names(deals: list[ComboDeal]) -> None:
    """Assign shortened display names to each deal for HTML output."""
    for deal in deals:
        deal.display_cpu = shorten_cpu(deal.cpu_name)  # type: ignore[attr-defined]
        deal.display_mb = shorten_motherboard(deal.motherboard_name)  # type: ignore[attr-defined]
        deal.display_ram = shorten_ram(deal.ram_name)  # type: ignore[attr-defined]


def _assign_row_classes(deals: list[ComboDeal]) -> None:
    """Assign row_class attribute to each deal based on savings percentage."""
    for deal in deals:
        pct = deal.savings_percent()
        if pct > 15:
            deal.row_class = "green"  # type: ignore[attr-defined]
        elif pct >= 5:
            deal.row_class = "yellow"  # type: ignore[attr-defined]
        else:
            deal.row_class = ""  # type: ignore[attr-defined]


def render_html_report(
    deals: list[ComboDeal],
    output_dir: str = "results",
) -> str:
    """Render deals to a timestamped HTML report file.

    Args:
        deals: List of ComboDeal objects to render.
        output_dir: Directory to write the HTML file into.

    Returns:
        Absolute path to the generated HTML file.
    """
    os.makedirs(output_dir, exist_ok=True)

    _assign_row_classes(deals)
    _assign_display_names(deals)

    # Compute summary stats
    best_savings = 0.0
    avg_savings = 0.0
    best_deal_name = "N/A"

    if deals:
        best_deal = max(deals, key=lambda d: d.savings)
        best_savings = best_deal.savings
        avg_savings = sum(d.savings for d in deals) / len(deals)
        best_deal_name = shorten_cpu(best_deal.cpu_name) or best_deal.combo_type

    now = datetime.now()
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    filename = f"deals_{now.strftime('%Y-%m-%d_%H%M')}.html"
    filepath = os.path.join(output_dir, filename)

    html = HTML_TEMPLATE.render(
        deals=deals,
        generated_at=generated_at,
        best_savings=best_savings,
        avg_savings=avg_savings,
        best_deal_name=best_deal_name,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def update_index(output_dir: str = "results") -> str:
    """Generate an index.html listing all report files in the output directory.

    Args:
        output_dir: Directory containing report HTML files.

    Returns:
        Absolute path to the generated index.html.
    """
    pattern = os.path.join(output_dir, "deals_*.html")
    report_files = sorted(
        [os.path.basename(f) for f in glob.glob(pattern)],
        reverse=True,
    )

    html = INDEX_TEMPLATE.render(reports=report_files)

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    return index_path
