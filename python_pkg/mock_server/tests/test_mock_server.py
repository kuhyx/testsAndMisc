"""Unit tests for mock_server module."""

from unittest.mock import MagicMock

from python_pkg.mock_server.mock_server import request


class TestRequest:
    """Tests for request function."""

    def test_intercepts_example_com(self) -> None:
        """Test that requests to example.com are intercepted."""
        flow = MagicMock()
        flow.request.host = "example.com"
        flow.response = None

        request(flow)

        # Response should be set
        assert flow.response is not None

    def test_returns_502_for_example_com(self) -> None:
        """Test that intercepted requests return 502 status."""
        flow = MagicMock()
        flow.request.host = "www.example.com"
        flow.response = None

        request(flow)

        # Check status code is 502
        assert flow.response is not None
        assert flow.response.status_code == 502

    def test_does_not_intercept_other_hosts(self) -> None:
        """Test that requests to other hosts are not intercepted."""
        flow = MagicMock()
        flow.request.host = "google.com"
        flow.response = None

        request(flow)

        # Response should remain None
        assert flow.response is None

    def test_intercepts_subdomains_of_example_com(self) -> None:
        """Test that subdomains of example.com are also intercepted."""
        flow = MagicMock()
        flow.request.host = "api.example.com"
        flow.response = None

        request(flow)

        assert flow.response is not None

    def test_response_body_contains_simulated_message(self) -> None:
        """Test that response body contains failure message."""
        flow = MagicMock()
        flow.request.host = "example.com"
        flow.response = None

        request(flow)

        assert flow.response is not None
        assert b"Simulated connection failure" in flow.response.content

    def test_response_content_type_is_text_plain(self) -> None:
        """Test that response has correct content type."""
        flow = MagicMock()
        flow.request.host = "example.com"
        flow.response = None

        request(flow)

        # Check headers
        assert flow.response is not None
        assert flow.response.headers["Content-Type"] == "text/plain"
