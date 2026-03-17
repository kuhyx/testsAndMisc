"""Unit tests for lichess_bot lichess_api module (edge cases)."""

from __future__ import annotations

from http import HTTPStatus
import json
from unittest.mock import MagicMock, patch

import chess
import pytest
import requests

from python_pkg.lichess_bot.lichess_api import LichessAPI


class TestRequestEdgeCases:
    """Additional tests for _request edge cases."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_request_error_with_attribute_error_on_text(self, api: LichessAPI) -> None:
        """Test error response when text property raises AttributeError."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        # Make text property raise AttributeError when accessed
        del mock_response.text  # Remove the default mock
        type(mock_response).text = property(
            fget=lambda _self: (_ for _ in ()).throw(AttributeError("no text"))
        )

        with patch.object(api.session, "request", return_value=mock_response):
            result = api._request("GET", "http://test.com")

        assert result == mock_response

    def test_request_error_with_type_error_on_text(self, api: LichessAPI) -> None:
        """Test error response when text causes TypeError."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        # Make text return something that causes TypeError when sliced
        mock_response.text = 12345  # integer can't be sliced with [:200]

        with patch.object(api.session, "request", return_value=mock_response):
            result = api._request("GET", "http://test.com")

        assert result == mock_response


class TestStreamEventsNon429Error:
    """Test stream_events with non-429 HTTP errors."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_stream_events_raises_non_429_error(self, api: LichessAPI) -> None:
        """Test stream_events raises non-429 HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            response=MagicMock(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(api, "_request", return_value=mock_response),
            pytest.raises(requests.HTTPError),
        ):
            # Try to get the first event - should raise
            next(api.stream_events())


class TestJoinGameStreamEdgeCases:
    """Additional tests for join_game_stream edge cases."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_join_game_stream_skips_empty_lines(self, api: LichessAPI) -> None:
        """Test join_game_stream skips empty lines."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        event = json.dumps(
            {
                "type": "gameFull",
                "white": {"id": "my_user"},
                "black": {"id": "opponent"},
                "state": {"moves": ""},
            }
        )
        mock_response.iter_lines.return_value = iter(["", "", event])
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(api, "_request", return_value=mock_response),
            patch.object(api, "get_my_user_id", return_value="my_user"),
        ):
            __board, color = api.join_game_stream("game123", None)

        assert color == "white"

    def test_join_game_stream_skips_invalid_json(self, api: LichessAPI) -> None:
        """Test join_game_stream skips invalid JSON lines."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        event = json.dumps(
            {
                "type": "gameFull",
                "white": {"id": "my_user"},
                "black": {"id": "opponent"},
                "state": {"moves": ""},
            }
        )
        mock_response.iter_lines.return_value = iter(["not json", event])
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(api, "_request", return_value=mock_response),
            patch.object(api, "get_my_user_id", return_value="my_user"),
        ):
            __board, color = api.join_game_stream("game123", None)

        assert color == "white"

    def test_join_game_stream_skips_non_gamefull_events(self, api: LichessAPI) -> None:
        """Test join_game_stream skips non-gameFull events before gameFull."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        # Emit a non-gameFull event first, then gameFull
        non_game_full = json.dumps({"type": "gameState", "moves": "e2e4"})
        game_full = json.dumps(
            {
                "type": "gameFull",
                "white": {"id": "my_user"},
                "black": {"id": "opponent"},
                "state": {"moves": ""},
            }
        )
        mock_response.iter_lines.return_value = iter([non_game_full, game_full])
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(api, "_request", return_value=mock_response),
            patch.object(api, "get_my_user_id", return_value="my_user"),
        ):
            __board, color = api.join_game_stream("game123", None)

        assert color == "white"

    def test_join_game_stream_no_gamefull_event(self, api: LichessAPI) -> None:
        """Test join_game_stream when stream ends without gameFull event."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        # Only non-gameFull events, no gameFull - loop exhausts without break
        events = [
            json.dumps({"type": "gameState", "moves": "e2e4"}),
            json.dumps({"type": "chatLine", "text": "hello"}),
        ]
        mock_response.iter_lines.return_value = iter(events)
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(api, "_request", return_value=mock_response):
            board, color = api.join_game_stream("game123", "black")

        # When no gameFull is found, returns default/provided color
        assert color == "black"
        # Board should be empty since no moves were parsed
        assert board.fen() == chess.STARTING_FEN


class TestStreamGameEventsEdgeCases:
    """Additional tests for stream_game_events edge cases."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_stream_game_events_skips_empty_lines(self, api: LichessAPI) -> None:
        """Test stream_game_events skips empty lines."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.iter_lines.return_value = iter(
            ["", '{"type": "gameFull"}', "", '{"type": "gameState"}']
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(api, "_request", return_value=mock_response):
            events = list(api.stream_game_events("game123"))

        assert len(events) == 2

    def test_stream_game_events_skips_invalid_json(self, api: LichessAPI) -> None:
        """Test stream_game_events skips invalid JSON lines."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.iter_lines.return_value = iter(
            ['{"type": "gameFull"}', "invalid json", '{"type": "gameState"}']
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(api, "_request", return_value=mock_response):
            events = list(api.stream_game_events("game123"))

        assert len(events) == 2
