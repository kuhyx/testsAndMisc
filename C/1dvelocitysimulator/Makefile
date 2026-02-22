CC := gcc
CFLAGS := -O2 -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE
LDFLAGS :=

SRC := main.c
BIN := 1dvelocitysimulator

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
