CC := gcc
CFLAGS := -O2 -Wall -Wextra -std=c11 $(shell pkg-config --cflags libwebsockets 2>/dev/null)
LDFLAGS := $(shell pkg-config --libs libwebsockets 2>/dev/null)

SRC := main.c
BIN := websocket_server

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
