"""
Script principal de execução manual e agendada.

Uso rápido (manual):
  python run.py                  # roda tudo
  python run.py instagram        # só Instagram
  python run.py ecommerce        # só e-commerce
  python run.py maps             # só localizações
  python run.py report           # só relatório no terminal
  python run.py schedule         # modo daemon — roda no horário configurado
"""
import sys

# Força UTF-8 no terminal Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console

console = Console()


def _run_instagram() -> None:
    from collectors.instagram import collect
    collect()


def _run_ecommerce() -> None:
    from collectors.ecommerce import collect
    collect()


def _run_maps() -> None:
    from collectors.google_maps import collect
    collect()


def _run_report() -> None:
    from reports.summary import run
    run()


def _run_all() -> None:
    console.rule("[bold cyan]Iniciando coleta completa[/bold cyan]")
    _run_instagram()
    _run_ecommerce()
    _run_maps()
    _run_report()


def _run_scheduled() -> None:
    import schedule
    import time
    from config import (
        SCHEDULE_SOCIAL_CRON,   # formato "HH:MM" simplificado
        SCHEDULE_ECOMMERCE_CRON,
    )

    # schedule lib usa formato simples; extraímos hora:minuto do cron
    def _hhmm(cron: str) -> str:
        parts = cron.split()
        return f"{parts[1].zfill(2)}:{parts[0].zfill(2)}"

    ig_time  = _hhmm(SCHEDULE_SOCIAL_CRON)
    ec_time  = _hhmm(SCHEDULE_ECOMMERCE_CRON)

    schedule.every().day.at(ig_time).do(_run_instagram)
    schedule.every().monday.at(ec_time).do(_run_ecommerce)
    schedule.every().monday.at(ec_time).do(_run_maps)

    console.print(
        f"[green]Scheduler iniciado[/green]\n"
        f"  Instagram: todo dia às {ig_time}\n"
        f"  E-commerce + Maps: toda segunda às {ec_time}\n"
        f"  Pressione Ctrl+C para parar."
    )

    while True:
        schedule.run_pending()
        time.sleep(60)


COMMANDS = {
    "instagram": _run_instagram,
    "ecommerce": _run_ecommerce,
    "maps":      _run_maps,
    "report":    _run_report,
    "schedule":  _run_scheduled,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "all":
        _run_all()
    elif cmd in COMMANDS:
        COMMANDS[cmd]()
    else:
        console.print(f"[red]Comando desconhecido:[/red] {cmd}")
        console.print(f"Disponíveis: {', '.join(['all'] + list(COMMANDS))}")
        sys.exit(1)
