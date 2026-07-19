from unittest.mock import MagicMock, patch

from sqlmodel import Session

import app.db as db
import app.settings_store as settings_store
from app.metadata import USER_AGENT, enrich_show, has_cached_overview, lookup_overview
from app.models import Show


def test_user_agent_includes_project_url():
    assert settings_store.GITHUB_URL in USER_AGENT
    assert settings_store.APP_VERSION in USER_AGENT


def test_has_cached_overview():
    assert has_cached_overview("Plot summary") is True
    assert has_cached_overview(None) is False
    assert has_cached_overview("") is False
    assert has_cached_overview("   ") is False


@patch("app.metadata.metadata_enabled", return_value=True)
@patch("app.metadata.httpx.Client")
def test_lookup_overview_uses_wikipedia_search_and_summary(mock_client_cls, _enabled):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = ["Breaking Bad (TV series)", ["Breaking Bad (TV series)"], [], []]

    mock_summary = MagicMock()
    mock_summary.status_code = 200
    mock_summary.raise_for_status = MagicMock()
    mock_summary.json.return_value = {"extract": "A chemistry teacher turns to crime."}

    instance = mock_client_cls.return_value.__enter__.return_value
    instance.get.side_effect = [mock_response, mock_summary]

    result = lookup_overview("Breaking Bad", "tv")

    assert result == "A chemistry teacher turns to crime."
    assert instance.get.call_count == 2
    assert mock_client_cls.call_args.kwargs["headers"]["User-Agent"] == USER_AGENT


@patch("app.metadata.lookup_overview", return_value="Fresh summary.")
@patch("app.metadata.metadata_enabled", return_value=True)
def test_enrich_show_refetches_when_overview_empty(mock_enabled, mock_lookup, client):
    with Session(db.engine) as session:
        show = Show(title="Breaking Bad", normalized_title="breaking-bad-refetch", overview="")
        session.add(show)
        session.commit()
        session.refresh(show)

        enrich_show(session, show)
        session.refresh(show)

        assert show.overview == "Fresh summary."
        mock_lookup.assert_called_once_with("Breaking Bad", "tv")


@patch("app.metadata.lookup_overview")
@patch("app.metadata.metadata_enabled", return_value=True)
def test_enrich_show_skips_when_overview_cached(mock_enabled, mock_lookup, client):
    with Session(db.engine) as session:
        show = Show(
            title="Breaking Bad",
            normalized_title="breaking-bad-cached",
            overview="Existing summary.",
        )
        session.add(show)
        session.commit()
        session.refresh(show)

        enrich_show(session, show)

        mock_lookup.assert_not_called()
