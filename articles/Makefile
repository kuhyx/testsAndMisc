CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -pedantic
LDFLAGS ?=

all: server_c

server_c: server_c.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

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
