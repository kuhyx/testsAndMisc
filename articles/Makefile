CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -pedantic
LDFLAGS ?=

all: server_c

server_c: server_c.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

lint:
	@echo "Running clang-tidy..."
	@clang-tidy -checks=-clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling server_c.c -- -std=gnu11 $(CFLAGS) $(LDFLAGS) || true
	@echo "Running cppcheck..."
	@cppcheck --enable=all --inconclusive --std=c11 --language=c --quiet --inline-suppr --check-level=exhaustive --suppress=missingIncludeSystem server_c.c || true

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
