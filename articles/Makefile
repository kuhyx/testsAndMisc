CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -pedantic
LDFLAGS ?=

.ONESHELL:

all: server_c

server_c: server_c.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

format:
	@command -v clang-format >/dev/null 2>&1 || { echo "clang-format not found"; exit 1; }
	@echo "Running clang-format (ColumnLimit=100)..."
	@clang-format -i -style=file server_c.c

format-check:
	@command -v clang-format >/dev/null 2>&1 || { echo "clang-format not found"; exit 1; }
	@echo "Checking formatting with clang-format..."
	@# Use clang-format dry-run so this works without git and doesn't depend on commit state
	@if clang-format --dry-run -Werror -style=file server_c.c >/dev/null 2>&1; then \
	  echo "Format check passed"; \
	else \
	  echo "Formatting changes needed (run 'make format')"; \
	  exit 1; \
	fi

# fail if any function exceeds 20 non-empty lines between '{' and matching '}'
funcsize-check:
	@echo "Checking function sizes (<= 20 lines)..."
	@command -v clang-tidy >/dev/null 2>&1 || { echo "clang-tidy not found"; exit 1; }
	@clang-tidy \
	  -checks=readability-function-size \
	  -warnings-as-errors=readability-function-size \
	  -config='{ "CheckOptions": [ { "key": "readability-function-size.LineThreshold", "value": "20" } ] }' \
	  server_c.c -- -std=gnu11 $(CFLAGS) $(LDFLAGS)

lint:
	@echo "Running clang-tidy..."
		@clang-tidy \
		  -checks=clang-analyzer-*,clang-diagnostic-*,readability-function-size,-clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling \
		  -config='{ "CheckOptions": [ { "key": "readability-function-size.LineThreshold", "value": "20" } ] }' \
		  server_c.c -- -std=gnu11 $(CFLAGS) $(LDFLAGS) || true
	@echo "Running cppcheck..."
	@cppcheck --enable=all --inconclusive --std=c11 --language=c --quiet --inline-suppr --check-level=exhaustive --suppress=missingIncludeSystem server_c.c || true
	@echo "Checking line length (<= 100 chars) in server_c.c..."
	@awk 'length($$0)>100{print "server_c.c:" NR ": line too long (" length($$0) " > 100)"; err=1} END{if(err){print "Line length check FAILED"; exit 1} else {print "Line length check passed"}}' server_c.c

build: minify

minify:
	npx -y html-minifier-terser \
	  --collapse-whitespace --remove-comments --remove-attribute-quotes \
	  --remove-redundant-attributes --minify-css true --minify-js true \
	  -o index.min.html index.html
	npx -y terser sw.js -o sw.min.js -c -m

clean:
	rm -f server_c

.PHONY: all clean
