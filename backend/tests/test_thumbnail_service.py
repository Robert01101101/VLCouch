from unittest.mock import patch

from sqlmodel import Session

import app.db as db
from app.models import Episode, Show
from app.thumbnail_service import (
    backfill_library_thumbnails,
    backfill_show_episode_thumbnails,
)


def test_backfill_library_thumbnails_skips_episodes(client):
    with patch("app.thumbnail_service.generate_movie_thumbnail_standalone") as mock_movie:
        with patch(
            "app.thumbnail_service.generate_show_thumbnail_for_show_standalone"
        ) as mock_show:
            with patch(
                "app.thumbnail_jobs.generate_episode_thumbnail_standalone"
            ) as mock_episode:
                mock_movie.return_value = True
                mock_show.return_value = True
                stats = backfill_library_thumbnails()

    assert "episodes" not in stats
    mock_movie.assert_called()
    mock_show.assert_called()
    mock_episode.assert_not_called()


def test_backfill_show_episode_thumbnails_only_for_requested_show(client):
    show_id = client.seed_data["show_id"]

    with Session(db.engine) as session:
        other_show = Show(title="Other Show", normalized_title="other-show")
        session.add(other_show)
        session.commit()
        session.refresh(other_show)
        session.add(
            Episode(
                show_id=other_show.id,
                season=1,
                episode=1,
                title="Pilot",
                file_path="c:/fixtures/tv/Other/S01E01.mkv",
            )
        )
        session.commit()

        with patch(
            "app.thumbnail_jobs.generate_episode_thumbnail_standalone"
        ) as mock_episode:
            mock_episode.return_value = True
            generated = backfill_show_episode_thumbnails(session, show_id)

    assert generated == 2
    assert mock_episode.call_count == 2
    called_ids = {call.args[0] for call in mock_episode.call_args_list}
    seed_episode_ids = set(client.seed_data["episode_ids"])
    assert called_ids == seed_episode_ids
