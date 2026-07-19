from sqlmodel import Session, select

import app.db as db
from app.library_progress import (
    find_in_progress_item,
    remaining_unwatched_episodes,
)
from app.models import Episode, WatchProgress
from app.watch_service import update_position


def test_find_in_progress_item(client):
    ep_id = client.seed_data["episode_ids"][1]
    with Session(db.engine) as session:
        update_position(session, "episode", ep_id, 600, 3600)

    with Session(db.engine) as session:
        progress = find_in_progress_item(session)
        assert progress is not None
        assert progress.item_id == ep_id
        assert progress.watched is False


def test_remaining_unwatched_episodes(client):
    show_id = client.seed_data["show_id"]
    ep_ids = client.seed_data["episode_ids"]

    with Session(db.engine) as session:
        from_ep = session.get(Episode, ep_ids[1])
        remaining = remaining_unwatched_episodes(session, show_id, from_ep)
        assert len(remaining) == 1
        assert remaining[0].id == ep_ids[1]

        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep_ids[0],
            )
        ).first()
        assert progress is not None
        assert progress.watched is True


def test_remaining_unwatched_includes_clicked_watched_episode(client):
    show_id = client.seed_data["show_id"]
    ep_ids = client.seed_data["episode_ids"]

    with Session(db.engine) as session:
        from_ep = session.get(Episode, ep_ids[0])
        remaining = remaining_unwatched_episodes(session, show_id, from_ep)
        assert [ep.id for ep in remaining] == ep_ids
