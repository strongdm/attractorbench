"""CLI for attractorbench: generate tasks, score results, compare runs."""

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
    individual: Annotated[bool, typer.Option("--individual", help="Generate tiers as separate tasks instead of combined full-stack")] = False,
    curriculum: Annotated[bool, typer.Option("--curriculum", help="Also generate optional curriculum subtier tasks")] = False,
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
    generated = generate_tasks(tier_defs, output_dir, fullstack=not individual, curriculum=curriculum)

    for slug in generated:
        task_dir = output_dir / slug
        if slug == "full-stack":
            from attractorbench.tiers import load_fullstack_tier
            fullstack_def = load_fullstack_tier()
            total_items = sum(t.total_items for t in fullstack_def.tiers)
            console.print(f"  [green]✓[/green] {slug}/ ({total_items} DoD items, {fullstack_def.agent_timeout}s timeout)")
        else:
            # Find the matching tier
            tier = next((t for t in tier_defs if t.slug == slug), None)
            if tier:
                console.print(f"  [green]✓[/green] {slug}/ ({tier.total_items} DoD items, {tier.agent_timeout}s timeout)")
            else:
                console.print(f"  [green]✓[/green] {slug}/")

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

    # Check if any results have per-tier breakdowns
    has_tiers = any(r.tier1_conformance is not None for r in results.values())

    table = Table(title=f"Results: {job_dir.name}")
    table.add_column("Task", style="bold")
    table.add_column("Build", justify="center")
    table.add_column("Self-Test", justify="right")
    if has_tiers:
        table.add_column("T1", justify="right")
        table.add_column("T2", justify="right")
        table.add_column("T3", justify="right")
    table.add_column("Conformance", justify="right")
    table.add_column("Composite", justify="right", style="bold")

    for task_name, reward in sorted(results.items()):
        build = "[green]✓[/green]" if reward.build_success else "[red]✗[/red]"
        row = [
            task_name,
            build,
            f"{reward.self_test_pass_rate:.1%}",
        ]
        if has_tiers:
            for tc in (reward.tier1_conformance, reward.tier2_conformance, reward.tier3_conformance):
                if tc is not None:
                    row.append(f"{tc.passed}/{tc.total} ({tc.pass_rate:.1%})")
                else:
                    row.append("-")
        row.extend([
            f"{reward.conformance_passed}/{reward.conformance_total} ({reward.conformance_pass_rate:.1%})",
            f"{reward.composite_score:.3f}",
        ])
        table.add_row(*row)

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
def leaderboard(
    job_dirs: Annotated[list[Path], typer.Argument(help="Paths to Harbor job directories")],
    sort: Annotated[str, typer.Option(help="Sort column: composite, cost, tokens, time, efficiency")] = "composite",
    include_curriculum: Annotated[bool, typer.Option("--include-curriculum", help="Include curriculum subtier tasks in rankings")] = False,
    markdown: Annotated[bool, typer.Option("--markdown", help="Output markdown table")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Rank agent+model combinations across runs with efficiency metrics."""
    from attractorbench.leaderboard import (
        SORT_COLUMNS,
        build_leaderboard,
        render_markdown,
        render_table,
        sort_leaderboard,
    )

    missing = [p for p in job_dirs if not p.exists() or not p.is_dir()]
    if missing:
        for p in missing:
            console.print(f"[red]Job directory not found: {p}[/red]")
        raise typer.Exit(1)

    if sort not in SORT_COLUMNS:
        console.print(f"[red]Invalid sort column: {sort}. Choose from: {', '.join(SORT_COLUMNS)}[/red]")
        raise typer.Exit(1)

    lb = build_leaderboard(job_dirs, include_curriculum=include_curriculum)

    if not lb.entries:
        console.print("[red]No results found in any job directory[/red]")
        raise typer.Exit(1)

    lb = sort_leaderboard(lb, sort)

    if json_output:
        console.print(lb.model_dump_json(indent=2))
    elif markdown:
        print(render_markdown(lb))
    else:
        render_table(lb, console)


@app.command()
def run_log(
    job_dirs: Annotated[list[Path], typer.Argument(help="Paths to Harbor job directories")],
    markdown: Annotated[bool, typer.Option("--markdown", help="Output markdown table")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """Log of individual benchmark runs with per-job totals."""
    import json

    from attractorbench.leaderboard import (
        build_run_log,
        render_run_log_markdown,
        render_run_log_table,
    )

    missing = [p for p in job_dirs if not p.exists() or not p.is_dir()]
    if missing:
        for p in missing:
            console.print(f"[red]Job directory not found: {p}[/red]")
        raise typer.Exit(1)

    entries = build_run_log(job_dirs)

    if not entries:
        console.print("[red]No results found in any job directory[/red]")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps([e.model_dump() for e in entries], indent=2))
    elif markdown:
        print(render_run_log_markdown(entries))
    else:
        render_run_log_table(entries, console)


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
