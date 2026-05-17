"""
Coleta métricas públicas do Instagram dos concorrentes via instaloader.
Não requer login para perfis públicos.
Salva snapshot diário em hb_snapshots_social.
"""
import time
import instaloader
from datetime import datetime, timezone
from rich.console import Console
from tenacity import retry, stop_after_attempt, wait_exponential

from config import COMPETITOR_IG_HANDLES, REQUEST_DELAY, IG_USERNAME, IG_PASSWORD
from storage.client import get_client, get_competitor_id, start_run, finish_run

console = Console()
loader = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    quiet=True,
)


def _login_if_configured() -> None:
    if IG_USERNAME and IG_PASSWORD:
        loader.login(IG_USERNAME, IG_PASSWORD)
        console.print(f"[green]Instagram: logado como {IG_USERNAME}[/green]")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=5, max=30))
def _fetch_profile(handle: str) -> instaloader.Profile:
    return instaloader.Profile.from_username(loader.context, handle)


def _engagement_rate(profile: instaloader.Profile) -> float | None:
    if profile.followers == 0:
        return None
    try:
        posts = list(profile.get_posts())[:12]
        if not posts:
            return None
        avg = sum(p.likes + p.comments for p in posts) / len(posts)
        return round(avg / profile.followers * 100, 3)
    except Exception:
        return None


def _avg_likes(profile: instaloader.Profile) -> float | None:
    try:
        posts = list(profile.get_posts())[:30]
        if not posts:
            return None
        return round(sum(p.likes for p in posts) / len(posts), 2)
    except Exception:
        return None


def _avg_comments(profile: instaloader.Profile) -> float | None:
    try:
        posts = list(profile.get_posts())[:30]
        if not posts:
            return None
        return round(sum(p.comments for p in posts) / len(posts), 2)
    except Exception:
        return None


def collect() -> dict:
    run_id = start_run("instagram")
    _login_if_configured()

    db = get_client()
    created = 0
    errors: list[str] = []

    for slug, handle in COMPETITOR_IG_HANDLES.items():
        console.print(f"[cyan]Instagram >> @{handle}[/cyan]")
        competitor_id = get_competitor_id(slug)
        if not competitor_id:
            console.print(f"  [yellow]slug '{slug}' não encontrado no banco[/yellow]")
            continue

        try:
            profile = _fetch_profile(handle)
            engagement = _engagement_rate(profile)
            avg_likes = _avg_likes(profile)
            avg_comments = _avg_comments(profile)

            snapshot = {
                "competitor_id":    competitor_id,
                "collected_at":     datetime.now(timezone.utc).isoformat(),
                "followers":        profile.followers,
                "following":        profile.followees,
                "posts_count":      profile.mediacount,
                "avg_likes_30d":    avg_likes,
                "avg_comments_30d": avg_comments,
                "engagement_rate":  engagement,
                "bio_text":         profile.biography[:500] if profile.biography else None,
                "external_url":     profile.external_url,
            }

            db.table("hb_snapshots_social").insert(snapshot).execute()

            # Atualiza também a tabela principal de concorrentes
            db.table("hb_competitors").update({
                "instagram_followers":      profile.followers,
                "instagram_engagement_rate": engagement,
                "updated_at":               datetime.now(timezone.utc).isoformat(),
            }).eq("id", competitor_id).execute()

            created += 1
            console.print(
                f"  [green]OK[/green] {profile.followers:,} seguidores | "
                f"eng {engagement}%"
            )

        except Exception as exc:
            msg = f"@{handle}: {exc}"
            errors.append(msg)
            console.print(f"  [red]ERRO[/red] {msg}")

        time.sleep(REQUEST_DELAY)

    status = "success" if not errors else ("partial" if created else "error")
    finish_run(
        run_id, status, created=created,
        error="; ".join(errors) if errors else None,
        metadata={"handles_attempted": len(COMPETITOR_IG_HANDLES), "errors": errors},
    )
    console.print(f"\n[bold]Instagram coletado:[/bold] {created} snapshots | status={status}")
    return {"created": created, "errors": errors}
