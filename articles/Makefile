CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -pedantic
LDFLAGS ?=

all: server_c

server_c: server_c.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f server_c

.PHONY: all clean
