CC := gcc
CFLAGS := -O2 -std=c11 -Wall -Wextra -Wno-unused-parameter
LDFLAGS :=

SRC := main.c movegen.c search.c
BIN := random_engine

# Perft driver
PERFT_SRC := perft.c movegen.c
PERFT_BIN := perft

.PHONY: all clean rebuild

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(PERFT_BIN): $(PERFT_SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(BIN) $(PERFT_BIN)

rebuild: clean all

.PHONY: perft
perft: $(PERFT_BIN)
