import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="openevals",
    help="OpenEvals — Open-source LLM Evaluation Framework",
    add_completion=False,
)
console = Console()

DEFAULT_METRICS = "faithfulness,relevance,hallucination,coherence,toxicity"


@app.command()
def evaluate(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Input prompt"),
    response: str = typer.Option(
        ..., "--response", "-r", help="Model response to evaluate"
    ),
    metrics: str = typer.Option(
        DEFAULT_METRICS, "--metrics", "-m", help="Comma-separated metrics"
    ),
    model: Optional[str] = typer.Option(None, "--model", help="Model name label"),
    context: Optional[str] = typer.Option(
        None, "--context", "-c", help="Context for RAG metrics"
    ),
    ground_truth: Optional[str] = typer.Option(
        None, "--ground-truth", "-g", help="Expected answer"
    ),
    output_json: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Evaluate a single prompt-response pair across multiple metrics."""
    metric_list = [m.strip() for m in metrics.split(",")]

    async def _run():
        from openevals.core import Evaluator

        evaluator = Evaluator(metrics=metric_list)
        return await evaluator.evaluate(
            prompt=prompt,
            response=response,
            context=context,
            ground_truth=ground_truth,
            model_name=model,
        )

    with Progress(
        SpinnerColumn(), TextColumn("[bold blue]Evaluating..."), transient=True
    ) as p:
        p.add_task("eval")
        result = asyncio.run(_run())

    if output_json:
        console.print_json(json.dumps(result.scores))
        return

    table = Table(title=f"[bold]OpenEvals Results[/bold]  model={model or 'unknown'}")
    table.add_column("Metric", style="cyan bold")
    table.add_column("Score", justify="right")
    table.add_column("95% CI", style="dim", justify="right")
    table.add_column("Explanation", style="dim")

    for mr in sorted(result.metric_results, key=lambda x: x.score, reverse=True):
        color = "green" if mr.score >= 0.7 else "yellow" if mr.score >= 0.4 else "red"
        table.add_row(
            mr.metric_name,
            f"[{color}]{mr.score:.3f}[/{color}]",
            f"[{mr.ci_lower:.3f}, {mr.ci_upper:.3f}]",
            (mr.explanation or "")[:60],
        )

    console.print(table)
    console.print(
        f"\n[dim]Total latency: {result.total_latency_ms:.0f}ms | {len(metric_list)} metrics[/dim]"
    )


@app.command()
def benchmark(
    models: str = typer.Option(
        "gpt-4o", "--models", help="Comma-separated model names"
    ),
    dataset: str = typer.Option(
        "truthfulqa", "--dataset", "-d", help="Dataset: truthfulqa, gsm8k, arc, mmlu"
    ),
    metrics: str = typer.Option(
        DEFAULT_METRICS, "--metrics", "-m", help="Metrics to evaluate"
    ),
    output: str = typer.Option(
        "benchmark_report.html", "--output", "-o", help="Output HTML report path"
    ),
    samples: int = typer.Option(
        100, "--samples", "-n", help="Number of dataset samples"
    ),
):
    """Run a full multi-model benchmark comparison with statistical significance testing."""
    model_list = [m.strip() for m in models.split(",")]
    console.print("\n[bold]OpenEvals Benchmark[/bold]")
    console.print(f"  Dataset:  [cyan]{dataset}[/cyan] ({samples} samples)")
    console.print(f"  Models:   [cyan]{', '.join(model_list)}[/cyan]")
    console.print(f"  Metrics:  [cyan]{metrics}[/cyan]")
    console.print(f"  Output:   [cyan]{output}[/cyan]\n")
    console.print("[yellow]Add API keys to .env to run live benchmark.[/yellow]")
    console.print(
        "[dim]openevals benchmark --models gpt-4o,claude-3-5-sonnet-20241022 --dataset truthfulqa[/dim]"
    )


@app.command()
def leaderboard(
    fmt: str = typer.Option(
        "table", "--format", "-f", help="Output format: table or json"
    ),
    host: str = typer.Option(
        "http://localhost:8000", "--host", help="OpenEvals server URL"
    ),
):
    """Show the live model leaderboard from the running OpenEvals server."""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"{host}/v1/rankings", timeout=5) as resp:
            payload = json.loads(resp.read())
        data = payload.get("leaderboard", [])
    except (urllib.error.URLError, Exception) as e:
        console.print(f"[red]Could not connect to {host}: {e}[/red]")
        console.print(
            "[dim]Start the server with: uvicorn openevals.api.main:app[/dim]"
        )
        raise typer.Exit(1)

    if not data:
        console.print(
            "[yellow]No evaluations yet. Submit some via POST /v1/evaluate.[/yellow]"
        )
        return

    if fmt == "json":
        console.print_json(json.dumps(data))
        return

    # Determine which metric columns are present across all models
    metric_cols = []
    for col in ["overall", "hallucination", "faithfulness", "relevance", "coherence"]:
        if any(col in row for row in data):
            metric_cols.append(col)

    table = Table(title="[bold]OpenEvals Live Model Leaderboard[/bold]")
    table.add_column("Rank", style="dim", justify="right")
    table.add_column("Model", style="cyan bold")
    for col in metric_cols:
        table.add_column(col.title(), justify="right")
    table.add_column("Evals", justify="right", style="dim")

    for row in data:
        color = (
            "green"
            if row.get("overall", 0) >= 0.85
            else "yellow" if row.get("overall", 0) >= 0.65 else "red"
        )
        metric_vals = [
            f"[{color}]{row[col]:.3f}[/{color}]" if col in row else "—"
            for col in metric_cols
        ]
        table.add_row(
            str(row["rank"]),
            row["model"],
            *metric_vals,
            str(row.get("eval_count", "—")),
        )

    console.print(table)
    console.print(
        f"\n[dim]{len(data)} model(s) · rankings update live as evaluations complete[/dim]"
    )


@app.command()
def metrics():
    """List all available evaluation metrics."""
    from openevals.metrics.registry import MetricRegistry

    registry = MetricRegistry()
    names = registry.list_available()
    table = Table(title="[bold]Available Metrics[/bold]")
    table.add_column("Metric", style="cyan bold")
    for name in sorted(names):
        table.add_row(name)
    console.print(table)


if __name__ == "__main__":
    app()
