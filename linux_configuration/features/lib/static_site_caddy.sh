#!/bin/bash
# Shared site-block body for the loopback static-site Caddies.
#
# Sourced by website_build.sh and kcd2_serve.sh, which each wrap this in their
# own global options and site address. One copy, because both serve a
# prerendered dist/ that must pass AgentReady (~/src/utils/agent_ready) and the
# two blocks drifting apart is how one of them grew an SPA catch-all.
#
# Check end to end with tests/e2e_agent_ready_caddy.sh website|dice.

# `serve` guard: refuse before docker sees the bind-mount source. A missing
# dist/ is not an error to compose -- docker creates it as an empty root-owned
# directory inside the repo and the site 404s while "running".
static_site_require_dist() {
	[[ -f "$1/index.html" ]] || die "No build at $1 — run setup first."
}

# Prints the directives that go inside the ":<port> { ... }" block.
static_site_caddy_body() {
	cat <<'EOF'
	root * /srv
	encode gzip
	# AgentReady FIND-04: advertise the AI catalog in an HTTP header as well
	# as in the page head.
	header Link "</.well-known/ai-catalog.json>; rel=\"ai-catalog\"; type=\"application/ai-catalog+json\""
	# Exact types the agent spec asks for. Go's defaults are text/xml and
	# application/json, and a .md would otherwise be guessed per platform.
	# The "file" matcher limits each to files that exist, so a missing
	# /x.md 404s as the HTML 404 page rather than as markdown.
	@md {
		path *.md
		file
	}
	header @md Content-Type "text/markdown; charset=utf-8"
	@txt {
		path /robots.txt /llms.txt
		file
	}
	header @txt Content-Type "text/plain; charset=utf-8"
	@sitemap {
		path /sitemap.xml
		file
	}
	header @sitemap Content-Type "application/xml"
	@catalog {
		path /.well-known/ai-catalog.json
		file
	}
	header @catalog Content-Type "application/ai-catalog+json"
	# {path}/index.html is the load-bearing middle term: every route is
	# prerendered to dist/<route>/index.html (blog posts, /how-it-works/),
	# and try_files does NOT resolve a directory to its index on its own.
	# Without it those pages 404 instead of serving their own HTML.
	#
	# There is deliberately no /index.html catch-all after it: that SPA
	# fallback answered every unknown path, robots.txt typo or probe with
	# "200 text/html", which agents read as a soft 404.
	try_files {path} {path}/index.html
	file_server
	# The prerendered 404 page, keeping the 404 status.
	handle_errors 404 {
		rewrite * /404.html
		file_server
	}
EOF
}
