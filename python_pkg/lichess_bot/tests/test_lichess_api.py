"""Unit tests for lichess_bot lichess_api module."""

# ruff: noqa: SLF001, S105, ARG001, PT012, TRY003, EM101, PERF402
# SLF001: Tests need to access private members to verify internal logic
# S105: Test tokens are not real passwords
# ARG001: Mock functions need *args, **kwargs signature
# PT012: pytest.raises can contain multiple statements for generator testing
# TRY003, EM101: Exception messages in tests are fine
# PERF402: We need loop append for generator consumption with exception break

from http import HTTPStatus
import json
from unittest.mock import MagicMock, patch

import chess
import pytest
import requests

from python_pkg.lichess_bot.lichess_api import LichessAPI


class _TestTerminationError(Exception):
    """Custom exception to break out of infinite loops in tests."""


class TestLichessAPIInit:
    """Tests for LichessAPI initialization."""

    def test_init_creates_session_with_headers(self) -> None:
        """Test initialization creates session with proper headers."""
        api = LichessAPI("test_token")

        assert api.token == "test_token"
        assert "Bearer test_token" in api.session.headers["Authorization"]
        assert "application/json" in api.session.headers["Accept"]

    def test_init_with_custom_session(self) -> None:
        """Test initialization with custom session."""
        custom_session = requests.Session()
        api = LichessAPI("test_token", session=custom_session)

        assert api.session is custom_session


class TestRequest:
    """Tests for _request method."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance with mocked session."""
        return LichessAPI("test_token")

    def test_request_success(self, api: LichessAPI) -> None:
        """Test successful request logs appropriately."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK

        with patch.object(api.session, "request", return_value=mock_response):
            result = api._request("GET", "http://test.com")

        assert result == mock_response

    def test_request_error_logs_body(self, api: LichessAPI) -> None:
        """Test error response logs body snippet."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.text = "Error message here"

        with patch.object(api.session, "request", return_value=mock_response):
            result = api._request("GET", "http://test.com")

        assert result == mock_response

    def test_request_error_no_body(self, api: LichessAPI) -> None:
        """Test error response without body."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        mock_response.text = None

        with patch.object(api.session, "request", return_value=mock_response):
            result = api._request("GET", "http://test.com")

        assert result == mock_response

    def test_request_raises_for_status(self, api: LichessAPI) -> None:
        """Test request raises for status when flag is set."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NOT_FOUND
        mock_response.text = ""
        mock_response.raise_for_status.side_effect = requests.HTTPError()

        with (
            patch.object(api.session, "request", return_value=mock_response),
            pytest.raises(requests.HTTPError),
        ):
            api._request("GET", "http://test.com", raise_for_status=True)

    def test_request_exception_handling(self, api: LichessAPI) -> None:
        """Test request handles exceptions."""
        with (
            patch.object(
                api.session, "request", side_effect=requests.ConnectionError()
            ),
            pytest.raises(requests.ConnectionError),
        ):
            api._request("GET", "http://test.com")


class TestStreamEvents:
    """Tests for stream_events method."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_stream_events_yields_json_lines(self, api: LichessAPI) -> None:
        """Test stream_events yields parsed JSON lines."""
        # stream_events has a while True loop, so we need to break out of it
        # by raising an exception after yielding our test data

        def iter_lines_with_stop(*args: object, **kwargs: object) -> list[str]:
            """Return lines then signal generator to stop."""
            return ['{"type": "challenge"}', "", '{"type": "gameStart"}']

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.iter_lines = iter_lines_with_stop
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def mock_request(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                # Break out of while True on second iteration
                raise _TestTerminationError("Test termination")
            return mock_response

        events_collected: list[dict] = []
        with (
            patch.object(api, "_request", side_effect=mock_request),
            pytest.raises(_TestTerminationError),
        ):
            for event in api.stream_events():
                events_collected.append(event)

        assert len(events_collected) == 2
        assert events_collected[0]["type"] == "challenge"
        assert events_collected[1]["type"] == "gameStart"

    def test_stream_events_skips_invalid_json(self, api: LichessAPI) -> None:
        """Test stream_events skips non-JSON lines."""

        def iter_lines_with_invalid(*args: object, **kwargs: object) -> list[str]:
            return ['{"type": "challenge"}', "not json", '{"type": "gameStart"}']

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.iter_lines = iter_lines_with_invalid
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def mock_request(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise _TestTerminationError("Test termination")
            return mock_response

        events_collected: list[dict] = []
        with (
            patch.object(api, "_request", side_effect=mock_request),
            pytest.raises(_TestTerminationError),
        ):
            for event in api.stream_events():
                events_collected.append(event)

        assert len(events_collected) == 2

    def test_stream_events_handles_rate_limit(self, api: LichessAPI) -> None:
        """Test stream_events backs off on rate limit."""
        mock_response_429 = MagicMock()
        mock_response_429.status_code = HTTPStatus.TOO_MANY_REQUESTS
        mock_response_429.raise_for_status.side_effect = requests.HTTPError(
            response=MagicMock(status_code=HTTPStatus.TOO_MANY_REQUESTS)
        )
        mock_response_429.__enter__ = MagicMock(return_value=mock_response_429)
        mock_response_429.__exit__ = MagicMock(return_value=False)

        def iter_lines_ok(*args: object, **kwargs: object) -> list[str]:
            return ['{"type": "test"}']

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = HTTPStatus.OK
        mock_response_ok.iter_lines = iter_lines_ok
        mock_response_ok.__enter__ = MagicMock(return_value=mock_response_ok)
        mock_response_ok.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def mock_request(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_response_429
            if call_count == 2:
                return mock_response_ok
            raise _TestTerminationError("Test termination")

        events_collected: list[dict] = []
        with (
            patch.object(api, "_request", side_effect=mock_request),
            patch("python_pkg.lichess_bot.lichess_api.time.sleep"),
            pytest.raises(_TestTerminationError),
        ):
            for event in api.stream_events():
                events_collected.append(event)

        assert len(events_collected) == 1
        assert call_count == 3  # 429 + OK + termination


class TestChallenges:
    """Tests for challenge-related methods."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_accept_challenge(self, api: LichessAPI) -> None:
        """Test accepting a challenge."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK

        with patch.object(api, "_request", return_value=mock_response) as mock_req:
            api.accept_challenge("test_challenge_id")

        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert "test_challenge_id" in call_args[0][1]
        assert call_args[1]["raise_for_status"] is True

    def test_decline_challenge(self, api: LichessAPI) -> None:
        """Test declining a challenge."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK

        with patch.object(api, "_request", return_value=mock_response) as mock_req:
            api.decline_challenge("test_challenge_id", reason="tooSlow")

        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert "decline" in call_args[0][1]
        assert call_args[1]["data"]["reason"] == "tooSlow"


class TestParseGameFullEvent:
    """Tests for _parse_game_full_event method."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_parse_game_full_as_white(self, api: LichessAPI) -> None:
        """Test parsing gameFull event when playing as white."""
        event = {
            "white": {"id": "my_user"},
            "black": {"id": "opponent"},
            "state": {"moves": "e2e4 e7e5"},
        }
        board = chess.Board()

        with patch.object(api, "get_my_user_id", return_value="my_user"):
            color = api._parse_game_full_event(event, board, "unknown")

        assert color == "white"
        assert len(board.move_stack) == 2

    def test_parse_game_full_as_black(self, api: LichessAPI) -> None:
        """Test parsing gameFull event when playing as black."""
        event = {
            "white": {"id": "opponent"},
            "black": {"id": "my_user"},
            "state": {"moves": ""},
        }
        board = chess.Board()

        with patch.object(api, "get_my_user_id", return_value="my_user"):
            color = api._parse_game_full_event(event, board, "unknown")

        assert color == "black"


class TestJoinGameStream:
    """Tests for join_game_stream method."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_join_game_stream(self, api: LichessAPI) -> None:
        """Test joining a game stream."""
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
        mock_response.iter_lines.return_value = iter([event])
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(api, "_request", return_value=mock_response),
            patch.object(api, "get_my_user_id", return_value="my_user"),
        ):
            board, color = api.join_game_stream("game123", None)

        assert color == "white"
        assert board.fen() == chess.STARTING_FEN


class TestStreamGameEvents:
    """Tests for stream_game_events method."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_stream_game_events_yields_events(self, api: LichessAPI) -> None:
        """Test stream_game_events yields parsed events."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.iter_lines.return_value = iter(
            ['{"type": "gameFull"}', '{"type": "gameState"}']
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(api, "_request", return_value=mock_response):
            events = list(api.stream_game_events("game123"))

        assert len(events) == 2


class TestMakeMove:
    """Tests for make_move method."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_make_move_success(self, api: LichessAPI) -> None:
        """Test successful move submission."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK

        with patch.object(api, "_request", return_value=mock_response):
            api.make_move("game123", chess.Move.from_uci("e2e4"))

    def test_make_move_conflict_raises(self, api: LichessAPI) -> None:
        """Test move submission with conflict."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.CONFLICT
        mock_response.raise_for_status.side_effect = requests.HTTPError()

        with (
            patch.object(api, "_request", return_value=mock_response),
            pytest.raises(requests.HTTPError),
        ):
            api.make_move("game123", chess.Move.from_uci("e2e4"))

    def test_make_move_rate_limit_retries(self, api: LichessAPI) -> None:
        """Test move submission retries on rate limit."""
        mock_response_429 = MagicMock()
        mock_response_429.status_code = HTTPStatus.TOO_MANY_REQUESTS

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = HTTPStatus.OK

        call_count = 0

        def mock_request(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_response_429
            return mock_response_ok

        with (
            patch.object(api, "_request", side_effect=mock_request),
            patch("python_pkg.lichess_bot.lichess_api.time.sleep"),
        ):
            api.make_move("game123", chess.Move.from_uci("e2e4"))

        assert call_count == 2

    def test_make_move_bad_request_raises(self, api: LichessAPI) -> None:
        """Test move submission with bad request raises but returns."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.raise_for_status.side_effect = requests.HTTPError()

        with (
            patch.object(api, "_request", return_value=mock_response),
            pytest.raises(requests.HTTPError),
        ):
            api.make_move("game123", chess.Move.from_uci("e2e4"))


class TestGetGameState:
    """Tests for get_game_state method."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_get_game_state_returns_none(self, api: LichessAPI) -> None:
        """Test deprecated get_game_state returns None."""
        result = api.get_game_state("game123")
        assert result is None


class TestGetMyUserId:
    """Tests for get_my_user_id method."""

    @pytest.fixture
    def api(self) -> LichessAPI:
        """Create API instance."""
        return LichessAPI("test_token")

    def test_get_my_user_id_success(self, api: LichessAPI) -> None:
        """Test getting user ID successfully."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.json.return_value = {"id": "my_username"}

        with patch.object(api, "_request", return_value=mock_response):
            user_id = api.get_my_user_id()

        assert user_id == "my_username"

    def test_get_my_user_id_failure(self, api: LichessAPI) -> None:
        """Test getting user ID when request fails."""
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.UNAUTHORIZED

        with patch.object(api, "_request", return_value=mock_response):
            user_id = api.get_my_user_id()

        assert user_id is None


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
