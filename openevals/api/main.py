from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from openevals.api.middleware.logging import LoggingMiddleware
from openevals.api.routers import (
    benchmark,
    bulk,
    datasets,
    evaluate,
    health,
    leaderboard,
    reports,
    webhooks,
)
from openevals.observability.logging import setup_logging

setup_logging()

app = FastAPI(
    title="OpenEvals API",
    description="Open-source LLM evaluation framework — 12 automated metrics, async pipeline, statistical rigor",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

app.include_router(health.router)
app.include_router(evaluate.router, prefix="/v1")
app.include_router(bulk.router, prefix="/v1")
app.include_router(reports.router, prefix="/v1")
app.include_router(benchmark.router, prefix="/v1")
app.include_router(datasets.router, prefix="/v1")
app.include_router(leaderboard.router, prefix="/v1")
app.include_router(webhooks.router, prefix="/v1")

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Serve dashboard
_DASHBOARD_DIR = Path(__file__).parent.parent.parent / "dashboard"
if _DASHBOARD_DIR.exists():
    app.mount(
        "/dashboard",
        StaticFiles(directory=str(_DASHBOARD_DIR), html=True),
        name="dashboard",
    )

    @app.get("/", include_in_schema=False)
    async def root():
        import json as _json

        from fastapi.responses import HTMLResponse

        from openevals.api.routers.evaluate import (
            _error_count,
            _recent_evals,
            _total_count,
        )
        from openevals.api.routers.leaderboard import get_leaderboard

        evals = list(_recent_evals)
        avg_latency = (
            round(sum(e["latency_ms"] for e in evals) / len(evals), 1) if evals else 0.0
        )
        error_rate = (
            round((_error_count / _total_count * 100), 3) if _total_count > 0 else 0.0
        )
        overall_scores = [e["overall_score"] for e in evals if e["overall_score"] > 0]
        avg_overall = (
            round(sum(overall_scores) / len(overall_scores), 4)
            if overall_scores
            else 0.0
        )
        totals: dict = {}
        for ev in evals:
            for metric, score in ev["scores"].items():
                totals.setdefault(metric, []).append(score)
        metrics_agg = {m: round(sum(v) / len(v), 4) for m, v in totals.items()}
        init_data = {
            "stats": {
                "total_evaluations": _total_count,
                "avg_latency_ms": avg_latency,
                "error_rate_pct": error_rate,
                "avg_overall_score": avg_overall,
                "session_evals_stored": len(evals),
            },
            "metrics": {"metrics": metrics_agg, "sample_size": len(evals)},
            "leaderboard": get_leaderboard(),
            "recent": evals[:6],
        }
        html = (_DASHBOARD_DIR / "index.html").read_text()
        # Inject data for JS live updates
        inject = f"<script>window.__INIT__={_json.dumps(init_data)};</script>"
        html = html.replace("</head>", inject + "</head>", 1)
        # Server-render key values directly into HTML (works even if JS/fetch blocked)
        html = html.replace(
            'class="conn-badge wait">connecting…<',
            'class="conn-badge ok">● Connected<',
            1,
        )
        html = html.replace(
            'class="sm-val" id="s-total">—<',
            f'class="sm-val" id="s-total">{_total_count}<',
            1,
        )
        html = html.replace(
            'id="s-lat">—<',
            f'id="s-lat">{avg_latency}ms<',
            1,
        )
        html = html.replace(
            'id="o-latency">—ms<',
            f'id="o-latency">{avg_latency}ms<',
            1,
        )
        html = html.replace(
            'id="s-err">—<',
            f'id="s-err">{error_rate}%<',
            1,
        )
        # Render leaderboard rows (replace skeleton content inside lb-rows div)
        import re as _re

        def _pill(s: float) -> str:
            return "pg" if s >= 0.85 else "py" if s >= 0.65 else "pr"

        _lb = get_leaderboard()
        lb_html = "".join(
            f'<div class="lb-row">'
            f'<span class="lb-rank">{r["rank"]}</span>'
            f'<i class="ti ti-cpu" style="font-size:12px;color:var(--muted)"></i>'
            f'<span class="lb-name">{r["model"]}</span>'
            f'<span class="pill {_pill(r["overall"])}">'
            f'{r["overall"]:.2f}</span></div>'
            for r in _lb
        )
        html = _re.sub(
            r'id="lb-rows">.*?</div>',
            f'id="lb-rows">{lb_html}</div>',
            html,
            count=1,
            flags=_re.DOTALL,
        )

        # Render recent evals (replace skeleton content inside recent-list div)
        def _sc(s: float) -> str:
            return "#4ade80" if s >= 0.85 else "#facc15" if s >= 0.65 else "#f87171"

        recent_html = "".join(
            f'<div class="ev-row">'
            f'<div class="sdot" style="background:{_sc(ev["overall_score"])}"></div>'
            f'<span class="ev-prompt" title="{ev["prompt"]}">{ev["prompt"][:60]}</span>'
            f'<span class="ev-score" style="color:{_sc(ev["overall_score"])}">'
            f'{ev["overall_score"]:.2f}</span></div>'
            for ev in evals[:6]
        )
        if recent_html:
            html = _re.sub(
                r'id="recent-list">.*?</div>',
                f'id="recent-list">{recent_html}</div>',
                html,
                count=1,
                flags=_re.DOTALL,
            )

        # Render metric bars (pure HTML — no Chart.js needed)
        _META = {
            "hallucination": (
                "Hallucination guard",
                "linear-gradient(90deg,#60a5fa,#3b82f6)",
            ),
            "coherence": ("Coherence", "linear-gradient(90deg,#2dd4bf,#0891b2)"),
            "conciseness": ("Conciseness", "linear-gradient(90deg,#a78bfa,#7c3aed)"),
            "latency": ("Latency score", "linear-gradient(90deg,#34d399,#059669)"),
            "faithfulness": ("Faithfulness", "linear-gradient(90deg,#4ade80,#22c55e)"),
            "relevance": ("Relevance", "linear-gradient(90deg,#facc15,#eab308)"),
            "toxicity": ("Toxicity guard", "linear-gradient(90deg,#fb923c,#f97316)"),
        }
        _ORDER = [
            "faithfulness",
            "relevance",
            "hallucination",
            "coherence",
            "toxicity",
            "conciseness",
            "latency",
        ]
        _FALLBACK_FILL = "rgba(255,255,255,.4)"
        if metrics_agg:
            bar_rows = "".join(
                f'<div class="bar-row">'
                f'<div class="bar-info"><div class="bar-top">'
                f'<span class="bar-name">{_META.get(k, (k, _FALLBACK_FILL))[0]}</span>'
                f'<span style="color:#fff;font-weight:500">{round(metrics_agg[k]*100)}%</span>'
                f'</div><div class="track"><div class="fill" style="width:{round(metrics_agg[k]*100)}%;'
                f'background:{_META.get(k, (k, _FALLBACK_FILL))[1]}"></div>'
                f"</div></div></div>"
                for k in _ORDER
                if k in metrics_agg
            )
            html = _re.sub(
                r'id="metric-bars">.*?</div>',
                f'id="metric-bars">{bar_rows}</div>',
                html,
                count=1,
                flags=_re.DOTALL,
            )
            html = html.replace(
                'id="m-sample">loading…<', f'id="m-sample">{len(evals)} evals<', 1
            )

        # Render overall score donut as SVG (no Chart.js needed)
        if overall_scores:
            overall_pct = round(avg_overall * 100)
            r_val, cx, cy = 54, 60, 60
            circ = 2 * 3.14159 * r_val
            filled = circ * overall_pct / 100
            donut_svg = (
                f'<svg width="120" height="120" viewBox="0 0 120 120" style="transform:rotate(-90deg)">'
                f'<circle cx="{cx}" cy="{cy}" r="{r_val}" fill="none" stroke="#1e3a5f" stroke-width="12"/>'
                f'<circle cx="{cx}" cy="{cy}" r="{r_val}" fill="none" stroke="#facc15" stroke-width="12"'
                f' stroke-dasharray="{filled:.1f} {circ:.1f}" stroke-linecap="round"/>'
                f"</svg>"
            )
            html = html.replace(
                '<canvas id="donutChart" width="120" height="120"></canvas>',
                donut_svg,
                1,
            )
            html = html.replace(
                'id="donut-num">—%<br>',
                f'id="donut-num">{overall_pct}%<br>',
                1,
            )
            html = html.replace(
                'id="donut-sub">loading…<',
                f'id="donut-sub">{_total_count:,} evals<',
                1,
            )

        return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


# ── Built-in test suite prompts ────────────────────────────────────────────────
_SEED_SAMPLES = [
    {
        "prompt": "What is the capital of France?",
        "response": "The capital of France is Paris, which has been the country's capital since the late 10th century.",
        "ground_truth": "Paris",
        "model_name": "claude-3-5-sonnet",
    },
    {
        "prompt": "Explain what machine learning is.",
        "response": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed, by training on data.",
        "ground_truth": "A subset of AI that learns from data",
        "model_name": "gpt-4o",
    },
    {
        "prompt": "What causes rainbows?",
        "response": "Rainbows are caused by the refraction, dispersion, and reflection of sunlight inside water droplets, splitting white light into its spectrum of colors.",
        "ground_truth": "Refraction and reflection of light in water droplets",
        "model_name": "gpt-4o-mini",
    },
    {
        "prompt": "Who wrote Romeo and Juliet?",
        "response": "Romeo and Juliet was written by William Shakespeare, believed to have been written between 1594 and 1596.",
        "ground_truth": "William Shakespeare",
        "model_name": "llama-3-70b",
    },
    {
        "prompt": "What is photosynthesis?",
        "response": "Photosynthesis is the process by which green plants, algae, and some bacteria convert sunlight, water, and carbon dioxide into glucose and oxygen.",
        "ground_truth": "Converting sunlight to energy in plants",
        "model_name": "mistral-7b",
    },
    {
        "prompt": "What is the boiling point of water?",
        "response": "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure.",
        "ground_truth": "100°C / 212°F at sea level",
        "model_name": "claude-3-5-sonnet",
    },
    {
        "prompt": "Who painted the Mona Lisa?",
        "response": "The Mona Lisa was painted by Leonardo da Vinci, created between approximately 1503 and 1519.",
        "ground_truth": "Leonardo da Vinci",
        "model_name": "gpt-4o",
    },
    {
        "prompt": "What planet is closest to the Sun?",
        "response": "Mercury is the closest planet to the Sun in our solar system.",
        "ground_truth": "Mercury",
        "model_name": "gpt-4o-mini",
    },
    {
        "prompt": "Explain what a neural network is.",
        "response": "A neural network is a computational model inspired by the human brain, consisting of layers of interconnected nodes that learn patterns from data through training.",
        "ground_truth": "A brain-inspired model for learning patterns",
        "model_name": "llama-3-70b",
    },
    {
        "prompt": "What is the speed of light?",
        "response": "The speed of light in a vacuum is approximately 299,792,458 metres per second, often rounded to 3×10⁸ m/s.",
        "ground_truth": "~299,792,458 m/s",
        "model_name": "mistral-7b",
    },
]


# ── Single-shot dashboard data endpoint (bypasses ad-blocker path filtering) ──
@app.get("/d", include_in_schema=False)
async def dashboard_data():
    """All dashboard data in one request — avoids ad-blocker path filtering."""
    from openevals.api.routers.evaluate import (
        _error_count,
        _history,
        _recent_evals,
        _total_count,
    )
    from openevals.api.routers.leaderboard import get_leaderboard

    evals = list(_recent_evals)
    avg_latency = (
        round(sum(e["latency_ms"] for e in evals) / len(evals), 1) if evals else 0.0
    )
    error_rate = (
        round((_error_count / _total_count * 100), 3) if _total_count > 0 else 0.0
    )
    overall_scores = [e["overall_score"] for e in evals if e["overall_score"] > 0]
    avg_overall = (
        round(sum(overall_scores) / len(overall_scores), 4) if overall_scores else 0.0
    )
    totals: dict = {}
    for ev in evals:
        for metric, score in ev["scores"].items():
            totals.setdefault(metric, []).append(score)
    metrics_agg = {m: round(sum(v) / len(v), 4) for m, v in totals.items()}
    h = _history[-100:]
    if len(h) > 50:
        step = max(1, len(h) // 50)
        h = h[::step]
    return {
        "stats": {
            "total_evaluations": _total_count,
            "avg_latency_ms": avg_latency,
            "error_rate_pct": error_rate,
            "avg_overall_score": avg_overall,
            "session_evals_stored": len(evals),
        },
        "metrics": {"metrics": metrics_agg, "sample_size": len(evals)},
        "leaderboard": get_leaderboard(),
        "recent": evals[:6],
        "history": h,
    }


# ── Server-side Quick Eval form handler (bypasses ABP fetch blocking) ──────────
@app.post("/eval", include_in_schema=False)
async def quick_eval_form(request: Request):
    """Accept a plain HTML form POST, run eval, redirect back with results."""
    import json as _json
    import time
    import urllib.parse

    from fastapi.responses import RedirectResponse

    from openevals.api.routers.evaluate import _store_result
    from openevals.core import Evaluator
    from openevals.types import EvaluationRequest

    form = await request.form()
    prompt = (form.get("prompt") or "").strip()
    response = (form.get("response") or "").strip()
    ground_truth = (form.get("ground_truth") or "").strip() or None
    model_name = (form.get("model_name") or "").strip() or None

    if not prompt or not response:
        return RedirectResponse("/?eval_error=missing_fields", status_code=303)

    try:
        req = EvaluationRequest(
            prompt=prompt,
            response=response,
            ground_truth=ground_truth,
            model_name=model_name,
        )
        t0 = time.perf_counter()
        evaluator = Evaluator(
            metrics=["hallucination", "coherence", "conciseness", "latency"]
        )
        result = await evaluator.evaluate_request(req)
        latency_ms = (time.perf_counter() - t0) * 1000
        result_dict = result.model_dump(mode="json")
        _store_result(req, result_dict, latency_ms)
        scores = {
            r["metric_name"]: round(r["score"] * 100)
            for r in result_dict.get("metric_results", [])
        }
        overall = round(sum(scores.values()) / len(scores)) if scores else 0
        payload = _json.dumps(
            {"scores": scores, "overall": overall, "latency_ms": round(latency_ms)}
        )
        return RedirectResponse(
            f"/?eval_result={urllib.parse.quote(payload)}", status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            f"/?eval_error={urllib.parse.quote(str(e))}", status_code=303
        )


# Built-in test suite exposed via API
@app.get("/v1/test-suite", include_in_schema=True, tags=["evaluate"])
async def get_test_suite():
    """Return the built-in prompt test suite for one-click benchmarking."""
    return {"items": _SEED_SAMPLES, "count": len(_SEED_SAMPLES)}


@app.on_event("startup")
async def seed_evaluations() -> None:
    """Run sample evaluations at startup so the dashboard has real data immediately."""
    import time

    from openevals.api.routers.evaluate import _store_result
    from openevals.core import Evaluator
    from openevals.types import EvaluationRequest

    async def _run_one(sample: dict) -> None:
        try:
            req = EvaluationRequest(
                prompt=sample["prompt"],
                response=sample["response"],
                ground_truth=sample.get("ground_truth"),
                model_name=sample.get("model_name"),
            )
            # Only lightweight heuristic metrics — no model downloads
            metrics = ["hallucination", "coherence", "conciseness", "latency"]
            t0 = time.perf_counter()
            evaluator = Evaluator(metrics=metrics)
            result = await evaluator.evaluate_request(req)
            latency_ms = (time.perf_counter() - t0) * 1000
            _store_result(req, result.model_dump(mode="json"), latency_ms)
        except Exception:
            pass

    await asyncio.gather(*[_run_one(s) for s in _SEED_SAMPLES])
