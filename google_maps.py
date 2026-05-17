"""
Busca lojas físicas de concorrentes via pesquisa web (sem API paga).
Raspa resultados de busca do Google para mapear localizações.
Salva/atualiza em hb_locations.
"""
import time
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from tenacity import retry, stop_after_attempt, wait_exponential

from config import USER_AGENT, REQUEST_DELAY, REQUEST_TIMEOUT
from storage.client import get_client, get_competitor_id, start_run, finish_run

console = Console()

SEARCH_QUERIES = [
    ("mamo",        "Mamo boutique lojas endereço São Paulo Alphaville Campinas"),
    ("femme-store", "Femme Store Multimarcas loja física endereço"),
    ("sl-store",    "SL Store loja roupa feminina endereço"),
    ("gerbella",    "Gerbella Multimarcas loja endereço"),
    ("loja-alegreto","Loja Alegreto roupa feminina endereço"),
]

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "pt-BR,pt;q=0.9",
}

CITY_STATES = {
    "São Paulo": "SP", "Campinas": "SP", "Barueri": "SP", "Alphaville": "SP",
    "Rio de Janeiro": "RJ", "Belo Horizonte": "MG", "Curitiba": "PR",
    "Porto Alegre": "RS", "Brasília": "DF", "Goiânia": "GO",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=5, max=20))
def _search(query: str) -> str:
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}&hl=pt-BR&gl=br"
    with httpx.Client(headers=HEADERS, follow_redirects=True) as http:
        r = http.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text


def _extract_addresses(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []

    for el in soup.find_all(string=True):
        text = el.strip()
        # Padrão "Rua/Av/Al + número, Cidade"
        if re.search(r"\b(Rua|Av\.|Avenida|Al\.|Alameda|R\.)\b", text, re.I):
            candidates.append(text[:200])
        # CEP
        if re.search(r"\d{5}-?\d{3}", text):
            candidates.append(text[:200])

    return list(dict.fromkeys(candidates))[:10]


def _detect_city_state(text: str) -> tuple[str | None, str | None]:
    for city, state in CITY_STATES.items():
        if city.lower() in text.lower():
            return city, state
    return None, None


def collect() -> dict:
    run_id = start_run("google_maps")
    db = get_client()
    created = 0
    errors: list[str] = []

    for slug, query in SEARCH_QUERIES:
        comp_id = get_competitor_id(slug)
        if not comp_id:
            continue

        console.print(f"[cyan]Maps >> {slug}[/cyan]")
        try:
            html      = _search(query)
            addresses = _extract_addresses(html)

            for addr in addresses:
                city, state = _detect_city_state(addr)
                if not city:
                    continue

                # Verifica se localização já existe
                existing = (
                    db.table("hb_locations")
                    .select("id")
                    .eq("competitor_id", comp_id)
                    .eq("city", city)
                    .execute()
                )
                if existing.data:
                    continue

                db.table("hb_locations").insert({
                    "competitor_id": comp_id,
                    "label":        f"{slug.replace('-', ' ').title()} — {city}",
                    "address":      addr[:300],
                    "city":         city,
                    "state":        state,
                    "region":       "Interior SP" if state == "SP" and city != "São Paulo" else state,
                    "store_type":   "standard",
                }).execute()
                created += 1
                console.print(f"  [green]+[/green] {city}/{state} — {addr[:60]}…")

        except Exception as exc:
            msg = f"{slug}: {exc}"
            errors.append(msg)
            console.print(f"  [red]ERRO[/red] {msg}")

        time.sleep(REQUEST_DELAY * 2)

    status = "success" if not errors else ("partial" if created else "error")
    finish_run(run_id, status, created=created, error="; ".join(errors) if errors else None)
    console.print(f"\n[bold]Maps coletado:[/bold] {created} localizações | status={status}")
    return {"created": created, "errors": errors}
