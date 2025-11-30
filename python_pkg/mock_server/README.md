# Simulate Connection Failure

(it takes ≈ 1hr to get it working)

Install: https://mitmproxy.org/ (install it the way they recommend for your OS, for Ubuntu specifically apt version is 4 main versions behind newest version)

Run it using `mitmproxy`

Run your webbrowser using `127.0.0.1:8080` as proxy
on chromium-based browser it should be enough to do:
`google-chrome --proxy-server=127.0.0.1:8080`

Run `mitmweb`

open 127.0.0.1:808**1**

Click `File` in upper left corner and then `Install Certificates`

You should get a list of Windows/Linux/macOS/Firefox with certificates and how to install them

Install certificates using those instructions

**important!** Go to your browser certificate settings and ensure that:

1. mitmproxy certificate is imported
2. **it is set to trusted**

Now all of your network communication should go through mitmproxy, you can verify it by going to 127.0.0.1:808**1** and seeing constant flow of requests

## What can we do with it?

1. Install mitmproxy python library using pip

`pip install mitmproxy`

2. Copy and paste this “hello world”:

```
from mitmproxy import http

def request(flow: http.HTTPFlow) -> None:
    # Only intercept traffic to example.com
    if "example.com" in flow.request.host:
        flow.response = http.Response.make(
            502,  # Bad Gateway status code
            b"Simulated connection failure",
            {"Content-Type": "text/plain"}
        )

```

3. Run it: `mitmdump -s mitm_world.py`
4. Go to [example.com](http://example.com)
5. You should see “simulated connection failure” in plain text
