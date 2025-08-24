# Minimal Makefile for the simple OpenGL FPS demo
# Targets: build (default), run, clean

CC := gcc
CFLAGS := -O2 -Wall -Wextra -Wno-missing-field-initializers -std=c11
LDFLAGS := -lglut -lGLU -lGL -lm

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
