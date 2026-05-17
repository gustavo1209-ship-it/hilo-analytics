from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def start_run(collector: str) -> int:
    db = get_client()
    res = (
        db.table("hb_collection_runs")
        .insert({"collector": collector, "status": "running"})
        .execute()
    )
    return res.data[0]["id"]


def finish_run(
    run_id: int,
    status: str,
    created: int = 0,
    updated: int = 0,
    error: str | None = None,
    metadata: dict | None = None,
) -> None:
    from datetime import datetime, timezone

    db = get_client()
    db.table("hb_collection_runs").update(
        {
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "records_created": created,
            "records_updated": updated,
            "error_message": error,
            "metadata": metadata or {},
        }
    ).eq("id", run_id).execute()


def get_competitor_id(slug: str) -> int | None:
    db = get_client()
    res = db.table("hb_competitors").select("id").eq("slug", slug).execute()
    return res.data[0]["id"] if res.data else None


def get_brand_id(brand_name: str) -> int | None:
    db = get_client()
    res = (
        db.table("hb_brands")
        .select("id")
        .ilike("name", brand_name)
        .execute()
    )
    return res.data[0]["id"] if res.data else None
