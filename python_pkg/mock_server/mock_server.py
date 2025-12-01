"""Mitmproxy addon to simulate connection failures."""

from mitmproxy import http  # pylint: disable=import-error


def request(flow: http.HTTPFlow) -> None:
    """Intercept requests and simulate failures for specific hosts."""
    # Only intercept traffic to example.com
    if "example.com" in flow.request.host:
        flow.response = http.Response.make(
            502,  # Bad Gateway status code
            b"Simulated connection failure",
            {"Content-Type": "text/plain"},
        )
