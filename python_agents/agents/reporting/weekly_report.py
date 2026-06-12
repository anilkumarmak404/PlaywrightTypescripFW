from __future__ import annotations

from datetime import datetime, timezone

from ..maintenance.enterprise import result_summary
from ..shared.io_utils import write_text
from ..shared.models import NormalizedTestResult


def generate_weekly_report(results: list[NormalizedTestResult]) -> dict:
    summary = result_summary(results)
    timestamp = datetime.now(timezone.utc).isoformat().replace(":", "-").replace(".", "-")
    html_path = f"reports/executive/python-weekly-quality-scorecard-{timestamp}.html"
    pdf_path = f"reports/executive/python-weekly-quality-scorecard-{timestamp}.pdf"

    html = build_scorecard_html(summary)
    written_html = write_text(html_path, html)
    written_latest_html = write_text("reports/executive/python-weekly-quality-scorecard.html", html)
    written_pdf = write_text(pdf_path, build_simple_pdf(summary).decode("latin-1"))
    written_latest_pdf = write_text("reports/executive/python-weekly-quality-scorecard.pdf", build_simple_pdf(summary).decode("latin-1"))

    return {
        "status": "generated",
        "htmlPath": str(written_html),
        "latestHtmlPath": str(written_latest_html),
        "pdfPath": str(written_pdf),
        "latestPdfPath": str(written_latest_pdf),
        "summary": summary,
    }


def build_scorecard_html(summary: dict) -> str:
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Weekly Quality Scorecard</title>
    <style>
      body {{ font-family: Arial, sans-serif; padding: 32px; color: #172b4d; }}
      .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
      .card {{ border: 1px solid #dfe1e6; border-radius: 6px; padding: 16px; }}
      .value {{ font-size: 32px; font-weight: 700; }}
      .green {{ color: #00875a; }}
      .red {{ color: #de350b; }}
      .blue {{ color: #0052cc; }}
    </style>
  </head>
  <body>
    <h1>Weekly Quality Scorecard</h1>
    <p>Generated: {datetime.now(timezone.utc).isoformat()}</p>
    <div class="grid">
      <div class="card"><h2>Total</h2><div class="value blue">{summary['total']}</div></div>
      <div class="card"><h2>Passed</h2><div class="value green">{summary['passed']}</div></div>
      <div class="card"><h2>Failed</h2><div class="value red">{summary['failed']}</div></div>
      <div class="card"><h2>Skipped</h2><div class="value">{summary['skipped']}</div></div>
      <div class="card"><h2>Flaky</h2><div class="value">{summary['flaky']}</div></div>
      <div class="card"><h2>Pass Rate</h2><div class="value green">{summary['passRate']:.2%}</div></div>
    </div>
  </body>
</html>
"""


def build_simple_pdf(summary: dict) -> bytes:
    lines = [
        "Weekly Quality Scorecard",
        f"Total: {summary['total']}",
        f"Passed: {summary['passed']}",
        f"Failed: {summary['failed']}",
        f"Skipped: {summary['skipped']}",
        f"Flaky: {summary['flaky']}",
        f"Pass Rate: {summary['passRate']:.2%}",
    ]
    text_commands = ["BT", "/F1 14 Tf", "72 760 Td"]
    for index, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index == 0:
            text_commands.append(f"({safe}) Tj")
        else:
            text_commands.append(f"0 -24 Td ({safe}) Tj")
    text_commands.append("ET")
    stream = "\n".join(text_commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)
