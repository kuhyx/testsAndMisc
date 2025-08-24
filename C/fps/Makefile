# Minimal Makefile for the simple OpenGL FPS demo
# Targets: build (default), run, clean

CC := gcc
CFLAGS := -O2 -Wall -Wextra -Wno-missing-field-initializers -std=c11 $(shell pkg-config --cflags sdl2 2>/dev/null)
LDFLAGS := -lglut -lGLU -lGL -lm $(shell pkg-config --libs sdl2 2>/dev/null)

SRC := main.c
BIN := fps_demo

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
