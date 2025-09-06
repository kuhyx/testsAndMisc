CC := gcc
CFLAGS := -O2 -std=c11 -Wall -Wextra -Wno-unused-parameter
LDFLAGS :=

SRC := main.c
BIN := random_engine

.PHONY: all clean rebuild

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(BIN)

rebuild: clean all
