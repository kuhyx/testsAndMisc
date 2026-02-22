CC := gcc
CFLAGS := -O2 -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE $(shell pkg-config --cflags libcurl libxml-2.0 2>/dev/null)
LDFLAGS := $(shell pkg-config --libs libcurl libxml-2.0 2>/dev/null)

SRC := scrape.c
BIN := scrape

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
