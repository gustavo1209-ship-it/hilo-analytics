"""
Coleta produtos e preços dos sites oficiais das marcas via API VTEX.
NV (bynv.com.br), John John (johnjohndenim.com.br), Calvin Klein (calvinklein.com.br)
todos usam VTEX com a mesma estrutura de API pública.
Salva em hb_scraped_products e registra histórico em hb_price_history.
"""
import time
from datetime import datetime, timezone

import httpx
from rich.console import Console
from tenacity import retry, stop_after_attempt, wait_exponential

from config import VTEX_TARGETS, USER_AGENT, REQUEST_DELAY, REQUEST_TIMEOUT
from storage.client import get_client, get_brand_id, start_run, finish_run

console = Console()

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

VTEX_SEARCH = "/api/catalog_system/pub/products/search"


# ---------- VTEX API ----------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=3, max=15))
def _vtex_page(client: httpx.Client, base_url: str, from_: int, to_: int) -> list[dict]:
    url = f"{base_url}{VTEX_SEARCH}?_from={from_}&_to={to_}"
    r = client.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json() if r.status_code in (200, 206) else []


def _extract_price(item_spec: dict) -> tuple[float | None, float | None]:
    """Retorna (preco_normal, preco_promocional)."""
    try:
        offer = item_spec["sellers"][0]["commertialOffer"]
        price      = offer.get("Price") or offer.get("ListPrice")
        list_price = offer.get("ListPrice")
        sale       = price if (list_price and price and price < list_price) else None
        base       = list_price if sale else price
        return (float(base) if base else None, float(sale) if sale else None)
    except (KeyError, IndexError, TypeError):
        return None, None


def _category_slug(categories: list[str]) -> str | None:
    """Mapeia caminho de categoria VTEX para slug local."""
    mapping = {
        "calca": "calca-jeans",
        "vestido": "vestido",
        "blusa": "blusa-top",
        "top": "blusa-top",
        "blazer": "blazer",
        "camisa": "camisa",
        "saia": "saia",
        "shorts": "shorts-bermuda",
        "bermuda": "shorts-bermuda",
        "macacao": "macacao",
        "macacão": "macacao",
        "underwear": "underwear",
        "intimo": "underwear",
        "bolsa": "bolsa",
        "calcado": "calcados",
        "tenis": "calcados",
        "sapato": "calcados",
    }
    for cat in categories:
        cat_lower = cat.lower()
        for keyword, slug in mapping.items():
            if keyword in cat_lower:
                return slug
    return None


def _parse_product(raw: dict, brand_slug: str) -> dict | None:
    name = raw.get("productName") or raw.get("productTitle")
    if not name:
        return None

    items = raw.get("items", [])
    price, sale = _extract_price(items[0]) if items else (None, None)
    if not price:
        return None

    categories = raw.get("categories", [])
    cat_slug = _category_slug(categories)

    return {
        "external_id":    str(raw.get("productId") or raw.get("productReference", ""))[:50],
        "name":           str(name)[:200],
        "price_brl":      price,
        "price_sale_brl": sale,
        "category_slug":  cat_slug,
        "url":            raw.get("link", "")[:500],
        "image_url":      (items[0].get("images", [{}])[0].get("imageUrl") if items else None),
    }


# ---------- upsert ----------

def _upsert_product(db, competitor_id: int, brand_id: int | None, item: dict) -> tuple[int, bool]:
    now = datetime.now(timezone.utc).isoformat()

    existing = (
        db.table("hb_scraped_products")
        .select("id")
        .eq("competitor_id", competitor_id)
        .eq("external_id", item["external_id"])
        .execute()
    )

    if existing.data:
        db.table("hb_scraped_products").update({
            "price_brl":      item["price_brl"],
            "price_sale_brl": item["price_sale_brl"],
            "last_seen_at":   now,
        }).eq("id", existing.data[0]["id"]).execute()
        return existing.data[0]["id"], False

    res = db.table("hb_scraped_products").insert({
        "competitor_id":  competitor_id,
        "brand_id":       brand_id,
        "external_id":    item["external_id"],
        "name":           item["name"],
        "category_slug":  item.get("category_slug"),
        "price_brl":      item["price_brl"],
        "price_sale_brl": item["price_sale_brl"],
        "url":            item["url"],
        "image_url":      item.get("image_url"),
        "first_seen_at":  now,
        "last_seen_at":   now,
    }).execute()
    return res.data[0]["id"], True


def _record_price(db, product_id: int, item: dict) -> None:
    db.table("hb_price_history").insert({
        "product_id":     product_id,
        "price_brl":      item["price_brl"],
        "price_sale_brl": item["price_sale_brl"],
        "in_stock":       True,
        "recorded_at":    datetime.now(timezone.utc).isoformat(),
    }).execute()


# ---------- coleta principal ----------

def collect() -> dict:
    run_id = start_run("ecommerce_vtex")
    db = get_client()
    total_created = total_updated = 0
    errors: list[str] = []

    with httpx.Client(headers=HEADERS, follow_redirects=True) as http:
        for target in VTEX_TARGETS:
            brand_slug = target["brand_slug"]
            brand_name = target["brand_name"]
            base_url   = target["vtex_url"]
            page_size  = target.get("page_size", 50)
            brand_id   = get_brand_id(brand_name)

            # Para VTEX, usamos competitor_id = brand_id porque o site é da própria marca
            # Criamos um concorrente virtual se não existir
            comp = (
                db.table("hb_competitors")
                .select("id")
                .eq("slug", f"site-{brand_slug}")
                .execute()
            )
            if comp.data:
                comp_id = comp.data[0]["id"]
            else:
                res = db.table("hb_competitors").insert({
                    "name":          f"{brand_name} (Site Oficial)",
                    "slug":          f"site-{brand_slug}",
                    "type":          "online",
                    "scope":         "national",
                    "ecommerce_url": base_url,
                }).execute()
                comp_id = res.data[0]["id"]

            console.print(f"\n[bold cyan]{brand_name}[/bold cyan] ({base_url})")

            from_ = 0
            page_created = page_updated = 0

            while True:
                to_ = from_ + page_size - 1
                try:
                    products_raw = _vtex_page(http, base_url, from_, to_)
                except Exception as exc:
                    errors.append(f"{brand_name} pag {from_}: {exc}")
                    console.print(f"  [red]ERRO pag {from_}:[/red] {exc}")
                    break

                if not products_raw:
                    break

                for raw in products_raw:
                    item = _parse_product(raw, brand_slug)
                    if not item:
                        continue
                    try:
                        product_id, is_new = _upsert_product(db, comp_id, brand_id, item)
                        _record_price(db, product_id, item)
                        if is_new:
                            page_created += 1
                            total_created += 1
                        else:
                            page_updated += 1
                            total_updated += 1
                    except Exception as e:
                        console.print(f"  [red]upsert:[/red] {e}")

                console.print(
                    f"  pag {from_}-{to_}: {len(products_raw)} recebidos | "
                    f"+{page_created} novos / ~{page_updated} atualizados"
                )

                if len(products_raw) < page_size:
                    break

                from_ += page_size
                time.sleep(REQUEST_DELAY)

    status = "success" if not errors else ("partial" if total_created + total_updated else "error")
    finish_run(
        run_id, status,
        created=total_created,
        updated=total_updated,
        error="; ".join(errors) if errors else None,
    )
    console.print(
        f"\n[bold]E-commerce coletado:[/bold] {total_created} novos | "
        f"{total_updated} atualizados | status={status}"
    )
    return {"created": total_created, "updated": total_updated, "errors": errors}
