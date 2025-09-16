CC := gcc
CFLAGS := -O2 -Wall -Wextra -std=c11

# SDL2 flags: require sdl2-config (no fallback)
SDL2CONF := $(shell command -v sdl2-config 2>/dev/null)
ifeq ($(SDL2CONF),)
$(error sdl2-config not found. Please install SDL2 development package.)
endif
SDL_CFLAGS := $(shell sdl2-config --cflags)
SDL_LDFLAGS := $(shell sdl2-config --libs)

SRC := main.c gui.c engine.c chess.c mistakes.c
OBJ := $(SRC:.c=.o)
BIN := opening_learner

.PHONY: all clean run

all: $(BIN)

$(BIN): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(SDL_LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) $(SDL_CFLAGS) -c -o $@ $<

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(OBJ) $(BIN)
