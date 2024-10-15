from mitmproxy import http

def request(flow: http.HTTPFlow) -> None:
    # Only intercept traffic to example.com
    if "example.com" in flow.request.host:
        flow.response = http.Response.make(
            502,  # Bad Gateway status code
            b"Simulated connection failure",
            {"Content-Type": "text/plain"}
        )
