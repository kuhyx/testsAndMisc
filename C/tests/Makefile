CC := gcc
CFLAGS := -O2 -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE
LDFLAGS :=

SRC := generatingPolishLettersOnWindowsTerminal.c
BIN := polish_letters

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
