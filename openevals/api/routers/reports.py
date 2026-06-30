"""Generate a self-contained HTML report (print-to-PDF ready)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from openevals.api.routers.evaluate import _error_count, _recent_evals, _total_count

router = APIRouter()

_REPORT_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a202c; background: #fff; padding: 40px; max-width: 900px; margin: 0 auto; }
h1 { font-size: 28px; font-weight: 700; color: #0d2137; border-bottom: 3px solid #0891b2; padding-bottom: 10px; margin-bottom: 6px; }
.subtitle { font-size: 13px; color: #64748b; margin-bottom: 30px; }
h2 { font-size: 18px; font-weight: 600; color: #0d2137; margin: 28px 0 12px; border-left: 4px solid #facc15; padding-left: 10px; }
h3 { font-size: 14px; font-weight: 600; color: #374151; margin: 16px 0 8px; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge.green { background: #dcfce7; color: #166534; }
.badge.yellow { background: #fef9c3; color: #854d0e; }
.badge.blue { background: #dbeafe; color: #1e40af; }
.badge.red { background: #fee2e2; color: #991b1b; }
.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }
.stat-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; text-align: center; }
.stat-box .val { font-size: 26px; font-weight: 700; color: #0d2137; }
.stat-box .lbl { font-size: 11px; color: #64748b; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px; }
th { background: #0d2137; color: #fff; padding: 10px 12px; text-align: left; font-weight: 600; }
td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }
tr:nth-child(even) td { background: #f8fafc; }
.bar-cell { display: flex; align-items: center; gap: 8px; }
.bar { height: 10px; border-radius: 5px; background: #0891b2; }
.finding-box { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.finding-box h3 { color: #0369a1; margin-top: 0; }
.finding-box p { font-size: 13px; color: #374151; line-height: 1.6; }
.footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }
@media print {
  body { padding: 20px; }
  .no-print { display: none; }
  h2 { break-before: avoid; }
  table { break-inside: avoid; }
}
.print-btn { background: #0891b2; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; font-size: 13px; cursor: pointer; margin-bottom: 24px; }
.print-btn:hover { background: #0e7490; }
"""


def _score_badge(s: float) -> str:
    cls = "green" if s >= 0.85 else ("yellow" if s >= 0.65 else "red")
    return f'<span class="badge {cls}">{s * 100:.1f}%</span>'


def _bar_html(s: float) -> str:
    pct = int(s * 100)
    color = "#4ade80" if s >= 0.85 else ("#facc15" if s >= 0.65 else "#f87171")
    return f'<div class="bar-cell"><div class="bar" style="width:{pct}px;background:{color}"></div><span>{pct}%</span></div>'  # noqa: E501


@router.get("/report", response_class=HTMLResponse)
async def generate_report():
    """Generate a print-ready HTML evaluation report."""
    from openevals.api.routers.leaderboard import get_leaderboard

    evals = list(_recent_evals)
    total = _total_count
    errors = _error_count
    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    # Aggregate metrics
    metric_totals: dict[str, list] = {}
    for ev in evals:
        for m, s in ev["scores"].items():
            metric_totals.setdefault(m, []).append(s)
    agg = {m: round(sum(v) / len(v), 4) for m, v in metric_totals.items()}
    overall = round(sum(agg.values()) / len(agg) * 100, 1) if agg else 0
    avg_latency = (
        round(sum(e["latency_ms"] for e in evals) / len(evals), 1) if evals else 0
    )

    # Live leaderboard from actual evaluations
    lb = get_leaderboard()

    # Key finding: derive from actual data
    if len(lb) >= 2:
        top = lb[0]
        second = lb[1]
        diff_pct = round((top["overall"] - second["overall"]) * 100, 1)
        finding_html = (
            f"<h3>Key Finding: {top['model']} leads with {top['overall']*100:.1f}% overall score</h3>"
            f"<p>Based on <b>{total} live evaluations</b> across {len(lb)} models, "
            f"<b>{top['model']}</b> scores <b>{top['overall']*100:.1f}%</b> vs "
            f"<b>{second['model']}</b> at <b>{second['overall']*100:.1f}%</b> "
            f"({diff_pct:+.1f}pp gap). Rankings update in real-time as evaluations complete.</p>"
        )
    elif len(lb) == 1:
        top = lb[0]
        finding_html = (
            f"<h3>Current Leader: {top['model']} ({top['overall']*100:.1f}% overall)</h3>"
            f"<p>Based on <b>{total} live evaluations</b>. Submit evaluations with different "
            f"model names to populate the full leaderboard.</p>"
        )
    else:
        finding_html = (
            "<h3>No evaluations yet</h3>"
            "<p>Submit evaluations via <code>POST /v1/evaluate</code> to populate this report.</p>"
        )

    # Metric rows
    metric_rows = (
        "".join(
            f"<tr><td><b>{m.replace('_',' ').title()}</b></td>"  # noqa: E231
            f"<td>{_bar_html(s)}</td>"
            f"<td>{_score_badge(s)}</td>"
            f"<td>{len(metric_totals.get(m,[]))}</td></tr>"  # noqa: E231
            for m, s in sorted(agg.items(), key=lambda x: -x[1])
        )
        if agg
        else "<tr><td colspan='4' style='text-align:center;color:#94a3b8'>No evaluations yet</td></tr>"
    )

    # Leaderboard rows
    metrics_to_show = ["hallucination", "faithfulness", "relevance", "coherence"]
    lb_header = "".join(
        f"<th>{m.replace('_', ' ').title()} ↑</th>" for m in metrics_to_show
    )
    lb_rows = (
        "".join(
            f"<tr><td>{r['rank']}</td><td><b>{r['model']}</b></td>"
            + "".join(
                f"<td>{_score_badge(r[m])}</td>" if m in r else "<td>—</td>"
                for m in metrics_to_show
            )
            + f"<td>{r.get('eval_count', 0)}</td></tr>"
            for r in lb
        )
        if lb
        else "<tr><td colspan='6' style='text-align:center;color:#94a3b8'>No model evaluations yet</td></tr>"
    )

    # Recent evals rows
    recent_rows = (
        "".join(
            f"<tr>"
            f"<td style='max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{ev['prompt']}</td>"  # noqa: E501
            f"<td>{ev.get('model_name') or '—'}</td>"
            f"<td>{_score_badge(ev['overall_score'])}</td>"
            f"<td>{ev['latency_ms']}ms</td>"
            f"<td style='font-size:11px;color:#94a3b8'>{ev['created_at'][:16].replace('T',' ')}</td>"  # noqa: E231,E501
            f"</tr>"
            for ev in evals[:15]
        )
        if evals
        else "<tr><td colspan='5' style='text-align:center;color:#94a3b8'>No evaluations yet</td></tr>"
    )

    error_rate = round(errors / total * 100, 2) if total > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>OpenEvals Report — {now}</title>
<style>{_REPORT_CSS}</style>
</head>
<body>
<button class="print-btn no-print" onclick="window.print()">&#11015; Download as PDF (Print &rarr; Save as PDF)</button>

<h1>OpenEvals Evaluation Report</h1>
<div class="subtitle">Generated {now} &middot; OpenEvals v0.1.0 &middot; github.com/Anubhav12123/openevals</div>

<h2>Executive Summary</h2>
<div class="summary-grid">
  <div class="stat-box"><div class="val">{total}</div><div class="lbl">Total Evaluations</div></div>
  <div class="stat-box"><div class="val">{overall}%</div><div class="lbl">Overall Score</div></div>
  <div class="stat-box"><div class="val">{avg_latency}ms</div><div class="lbl">Avg Latency</div></div>
  <div class="stat-box"><div class="val">{error_rate}%</div><div class="lbl">Error Rate</div></div>
</div>

<div class="finding-box">
  {finding_html}
</div>

<h2>Metric Performance</h2>
<table>
  <tr><th>Metric</th><th>Score</th><th>Rating</th><th>Sample Size</th></tr>
  {metric_rows}
</table>

<h2>Model Leaderboard (Live Rankings)</h2>
<table>
  <tr><th>#</th><th>Model</th>{lb_header}<th>Evals</th></tr>
  {lb_rows}
</table>

<h2>Recent Evaluations ({min(len(evals), 15)} of {total})</h2>
<table>
  <tr><th>Prompt</th><th>Model</th><th>Overall Score</th><th>Latency</th><th>Timestamp</th></tr>
  {recent_rows}
</table>

<h2>Methodology</h2>
<p style="font-size:13px;line-height:1.7;color:#374151">
Evaluations use a hybrid approach: heuristic fallbacks (entity overlap, length analysis, structural scoring)
are used when LLM judge API keys are not configured, and upgraded to GPT-4o / Claude judges when keys are
provided. Bootstrap confidence intervals (1,000 iterations) are computed for aggregate scores. Statistical
comparisons use Welch&apos;s t-test with Bonferroni correction for multiple comparisons.
</p>

<div class="footer">
  OpenEvals &middot; Open-source LLM Evaluation Framework &middot; Built by Anubhav Dixit, Michigan State University<br/>
  Apache 2.0 License &middot; github.com/Anubhav12123/openevals
</div>
</body>
</html>"""

    return HTMLResponse(content=html)
