"""CLI for attractorbench — generate tasks, score results, compare runs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="attractorbench", help="Benchmark for Attractor NLSpec coding agent compliance.")
console = Console()


def _parse_tier_numbers(raw_tiers: Optional[str]) -> list[int] | None:
    if raw_tiers is None:
        return None

    parsed: list[int] = []
    for token in raw_tiers.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            parsed.append(int(token))
        except ValueError as exc:
            raise typer.BadParameter(
                f"Invalid tier value '{token}'. Expected comma-separated integers like '1,2,3'."
            ) from exc

    if not parsed:
        raise typer.BadParameter("No tiers were provided. Use a value like '1' or '1,2,3'.")
    return parsed


@app.command()
def generate(
    tiers: Annotated[Optional[str], typer.Option(help="Comma-separated tier numbers (e.g. 1,2,3)")] = None,
    output_dir: Annotated[Path, typer.Option(help="Output directory for task dirs")] = Path("tasks"),
) -> None:
    """Generate Harbor-compatible task directories from specs."""
    from attractorbench.adapter import generate_tasks
    from attractorbench.tiers import load_tiers

    tier_numbers = _parse_tier_numbers(tiers)
    try:
        tier_defs = load_tiers(tier_numbers)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--tiers") from exc

    console.print(f"Generating tasks for {len(tier_defs)} tier(s)...")
    generate_tasks(tier_defs, output_dir)

    for tier in tier_defs:
        task_dir = output_dir / tier.slug
        console.print(f"  [green]✓[/green] {tier.slug}/ ({tier.total_items} DoD items, {tier.agent_timeout}s timeout)")

    console.print(f"\nTasks written to [bold]{output_dir}[/bold]")


@app.command()
def score(
    job_dir: Annotated[Path, typer.Argument(help="Path to a completed Harbor job directory")],
) -> None:
    """Score a completed Harbor job."""
    from attractorbench.scoring import load_job_results

    if not job_dir.exists() or not job_dir.is_dir():
        console.print(f"[red]Job directory not found: {job_dir}[/red]")
        raise typer.Exit(1)

    results = load_job_results(job_dir)

    if not results:
        console.print(f"[red]No reward.json files found in {job_dir}[/red]")
        raise typer.Exit(1)

    table = Table(title=f"Results: {job_dir.name}")
    table.add_column("Task", style="bold")
    table.add_column("Build", justify="center")
    table.add_column("Self-Test", justify="right")
    table.add_column("Conformance", justify="right")
    table.add_column("Composite", justify="right", style="bold")

    for task_name, reward in sorted(results.items()):
        build = "[green]✓[/green]" if reward.build_success else "[red]✗[/red]"
        table.add_row(
            task_name,
            build,
            f"{reward.self_test_pass_rate:.1%}",
            f"{reward.conformance_passed}/{reward.conformance_total} ({reward.conformance_pass_rate:.1%})",
            f"{reward.composite_score:.3f}",
        )

    console.print(table)

    count = len(results)
    avg_self = sum(reward.self_test_pass_rate for reward in results.values()) / count
    avg_conf = sum(reward.conformance_pass_rate for reward in results.values()) / count
    avg_composite = sum(reward.composite_score for reward in results.values()) / count
    build_rate = sum(1 for reward in results.values() if reward.build_success) / count

    summary = Table(title=f"Summary: {job_dir.name}")
    summary.add_column("Tasks", justify="right")
    summary.add_column("Build Pass", justify="right")
    summary.add_column("Avg Self-Test", justify="right")
    summary.add_column("Avg Conformance", justify="right")
    summary.add_column("Avg Composite", justify="right", style="bold")
    summary.add_row(
        str(count),
        f"{build_rate:.1%}",
        f"{avg_self:.1%}",
        f"{avg_conf:.1%}",
        f"{avg_composite:.3f}",
    )
    console.print(summary)


@app.command()
def compare(
    job_dirs: Annotated[list[Path], typer.Argument(help="Paths to Harbor job directories to compare")],
) -> None:
    """Compare results across multiple Harbor job runs."""
    from attractorbench.scoring import compare_jobs

    missing = [path for path in job_dirs if not path.exists() or not path.is_dir()]
    if missing:
        for path in missing:
            console.print(f"[red]Job directory not found: {path}[/red]")
        raise typer.Exit(1)

    rows = compare_jobs(job_dirs)

    if not rows:
        console.print("[red]No results found in any job directory[/red]")
        raise typer.Exit(1)

    table = Table(title="Comparison")
    table.add_column("Job", style="bold")
    table.add_column("Task")
    table.add_column("Build", justify="center")
    table.add_column("Self-Test", justify="right")
    table.add_column("Conformance", justify="right")
    table.add_column("Composite", justify="right", style="bold")

    for row in sorted(rows, key=lambda row: (row["job"], row["task"])):
        build = "[green]✓[/green]" if row["build_success"] else "[red]✗[/red]"
        table.add_row(
            row["job"],
            row["task"],
            build,
            f"{row['self_test_pass_rate']:.1%}",
            f"{row['conformance_pass_rate']:.1%}",
            f"{row['composite_score']:.3f}",
        )

    console.print(table)

    by_job: dict[str, list[dict]] = {}
    for row in rows:
        by_job.setdefault(row["job"], []).append(row)

    summary = Table(title="Job Summary")
    summary.add_column("Job", style="bold")
    summary.add_column("Tasks", justify="right")
    summary.add_column("Build Pass", justify="right")
    summary.add_column("Avg Self-Test", justify="right")
    summary.add_column("Avg Conformance", justify="right")
    summary.add_column("Avg Composite", justify="right", style="bold")

    for job, job_rows in sorted(by_job.items()):
        task_count = len(job_rows)
        build_rate = sum(1 for row in job_rows if row["build_success"]) / task_count
        avg_self = sum(row["self_test_pass_rate"] for row in job_rows) / task_count
        avg_conf = sum(row["conformance_pass_rate"] for row in job_rows) / task_count
        avg_composite = sum(row["composite_score"] for row in job_rows) / task_count
        summary.add_row(
            job,
            str(task_count),
            f"{build_rate:.1%}",
            f"{avg_self:.1%}",
            f"{avg_conf:.1%}",
            f"{avg_composite:.3f}",
        )

    console.print(summary)


@app.command()
def checklist(
    tier: Annotated[Optional[int], typer.Option(help="Tier number (1, 2, or 3)")] = None,
) -> None:
    """List Definition of Done checklists."""
    from attractorbench.tiers import load_tiers

    tier_numbers = [tier] if tier else None
    try:
        tier_defs = load_tiers(tier_numbers)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--tier") from exc

    for tier_def in tier_defs:
        console.print(f"\n[bold]Tier {tier_def.tier}: {tier_def.name}[/bold] ({tier_def.total_items} items)")
        console.print(f"  Spec: {tier_def.spec_file}")
        console.print(f"  Timeout: {tier_def.agent_timeout}s")
        console.print()

        for section in tier_def.sections:
            console.print(f"  [bold]{section.number} {section.name}[/bold] ({len(section.items)} items)")
            for item in section.items:
                prefix = "  [dim]M[/dim]" if item.is_matrix else "  [ ]"
                console.print(f"    {prefix} {item.text}")
            console.print()


if __name__ == "__main__":
    app()
