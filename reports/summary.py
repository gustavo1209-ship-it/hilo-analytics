"""
Gera relatório de inteligência competitiva a partir dos dados do Supabase.
Pode ser rodado standalone ou importado.
"""
from datetime import datetime, timezone, timedelta
from rich.console import Console
from rich.table import Table
from rich import box

from storage.client import get_client

console = Console()


def _competitors_table() -> None:
    db = get_client()
    rows = db.table("hb_v_competitor_overview").select("*").execute().data

    t = Table(title="Concorrentes — Visão Geral", box=box.ROUNDED)
    t.add_column("Nome", style="bold")
    t.add_column("Tipo")
    t.add_column("Seguidores", justify="right")
    t.add_column("Eng %", justify="right")
    t.add_column("Ticket Médio", justify="right")
    t.add_column("Receita (R$M)", justify="right")

    for r in rows:
        t.add_row(
            r["name"],
            r["type"],
            f"{r['instagram_followers']:,}" if r.get("instagram_followers") else "—",
            f"{r['instagram_engagement_rate']}" if r.get("instagram_engagement_rate") else "—",
            f"R$ {r['ticket_avg_brl']:,.0f}" if r.get("ticket_avg_brl") else "—",
            f"{r['annual_revenue_brl']/1e6:,.0f}" if r.get("annual_revenue_brl") else "—",
        )
    console.print(t)


def _pricing_table() -> None:
    db = get_client()
    rows = db.table("hb_v_hilo_brands_pricing").select("*").execute().data

    t = Table(title="Preços — Marcas da Hilo por Categoria", box=box.ROUNDED)
    t.add_column("Marca", style="bold")
    t.add_column("Categoria")
    t.add_column("Mín", justify="right")
    t.add_column("Médio", justify="right")
    t.add_column("Máx", justify="right")
    t.add_column("Margem %", justify="right")

    for r in rows:
        t.add_row(
            r["marca"],
            r["categoria"],
            f"R$ {r['preco_min']:,.0f}" if r.get("preco_min") else "—",
            f"R$ {r['preco_medio']:,.0f}" if r.get("preco_medio") else "—",
            f"R$ {r['preco_max']:,.0f}" if r.get("preco_max") else "—",
            f"{r['margem_pct']}%" if r.get("margem_pct") else "—",
        )
    console.print(t)


def _growth_table() -> None:
    db = get_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    rows = (
        db.table("hb_snapshots_social")
        .select("competitor_id, followers, collected_at")
        .gte("collected_at", cutoff)
        .order("collected_at")
        .execute()
        .data
    )

    if not rows:
        console.print("[yellow]Sem snapshots nos últimos 30 dias ainda.[/yellow]")
        return

    # Agrupa por competitor e calcula delta
    from collections import defaultdict
    by_comp: dict[int, list] = defaultdict(list)
    for r in rows:
        by_comp[r["competitor_id"]].append(r)

    comp_names = {
        c["id"]: c["name"]
        for c in db.table("hb_competitors").select("id, name").execute().data
    }

    t = Table(title="Crescimento de Seguidores (30 dias)", box=box.ROUNDED)
    t.add_column("Concorrente", style="bold")
    t.add_column("Inicial", justify="right")
    t.add_column("Atual", justify="right")
    t.add_column("Delta", justify="right")
    t.add_column("% Crescimento", justify="right")

    for comp_id, snapshots in by_comp.items():
        if len(snapshots) < 2:
            continue
        first = snapshots[0]["followers"] or 0
        last  = snapshots[-1]["followers"] or 0
        delta = last - first
        pct   = round(delta / first * 100, 2) if first else 0
        color = "green" if delta >= 0 else "red"
        t.add_row(
            comp_names.get(comp_id, str(comp_id)),
            f"{first:,}",
            f"{last:,}",
            f"[{color}]{delta:+,}[/{color}]",
            f"[{color}]{pct:+.2f}%[/{color}]",
        )
    console.print(t)


def _insights_table() -> None:
    db = get_client()
    rows = (
        db.table("hb_v_priority_insights")
        .select("category, title, priority, action_items")
        .execute()
        .data
    )

    t = Table(title="Insights Prioritários — Ações para a Hilo", box=box.ROUNDED)
    t.add_column("Prioridade", justify="center")
    t.add_column("Categoria")
    t.add_column("Insight", style="bold")
    t.add_column("Ação Principal")

    COLORS = {"alta": "red", "media": "yellow", "baixa": "green"}

    for r in rows[:10]:
        color = COLORS.get(r["priority"], "white")
        first_action = (r.get("action_items") or "").split("\n")[0][:100]
        t.add_row(
            f"[{color}]{r['priority'].upper()}[/{color}]",
            r["category"].replace("_", " ").title(),
            r["title"][:60],
            first_action,
        )
    console.print(t)


def run() -> None:
    console.rule("[bold]HILO BOUTIQUE — Inteligência Competitiva[/bold]")
    console.print(f"[dim]Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}[/dim]\n")
    _competitors_table()
    console.print()
    _pricing_table()
    console.print()
    _growth_table()
    console.print()
    _insights_table()


if __name__ == "__main__":
    run()
