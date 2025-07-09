CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -O2
LIBS = -lSDL2 -lSDL2_image -lm
TARGET = imageviewer
SOURCE = main.c

# Check if pkg-config is available for SDL2
SDL2_CFLAGS := $(shell pkg-config --cflags sdl2 2>/dev/null)
SDL2_LIBS := $(shell pkg-config --libs sdl2 2>/dev/null)

# If pkg-config found SDL2, use it
ifneq ($(SDL2_CFLAGS),)
    CFLAGS += $(SDL2_CFLAGS)
    LIBS = $(SDL2_LIBS) -lSDL2_image -lm
endif

.PHONY: all clean install deps help

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE) $(LIBS)

clean:
	rm -f $(TARGET)

# Install dependencies on Ubuntu/Debian
deps-debian:
	sudo apt-get update
	sudo apt-get install libsdl2-dev libsdl2-image-dev

# Install dependencies on Fedora/RHEL/CentOS
deps-fedora:
	sudo dnf install SDL2-devel SDL2_image-devel

# Install dependencies on Arch Linux
deps-arch:
	sudo pacman -S sdl2 sdl2_image

# Run with a test image
test:
	@if [ -f $(TARGET) ]; then \
		echo "Looking for test images..."; \
		if [ -d "../misc/randomJPG/14k" ] && [ -n "$$(ls ../misc/randomJPG/14k/*.jpg 2>/dev/null | head -1)" ]; then \
			echo "Running with test image from randomJPG folder..."; \
			./$(TARGET) $$(ls ../misc/randomJPG/14k/*.jpg | head -1); \
		else \
			echo "No test images found. Please run: ./$(TARGET) <image_file.jpg>"; \
		fi \
	else \
		echo "Build the project first: make"; \
	fi

help:
	@echo "JPG Image Viewer - Makefile targets:"
	@echo "  all          - Build the image viewer"
	@echo "  clean        - Remove built files"
	@echo "  test         - Run with a test image (if available)"
	@echo "  deps-debian  - Install dependencies on Ubuntu/Debian"
	@echo "  deps-fedora  - Install dependencies on Fedora/RHEL/CentOS"
	@echo "  deps-arch    - Install dependencies on Arch Linux"
	@echo "  help         - Show this help"
	@echo ""
	@echo "Usage: ./$(TARGET) <image_file.jpg>"
	@echo ""
	@echo "Controls:"
	@echo "  Mouse wheel / +/- : Zoom in/out"
	@echo "  Mouse drag        : Pan image"
	@echo "  R                 : Reset zoom and position"
	@echo "  F                 : Fit image to window"
	@echo "  H                 : Show help"
	@echo "  ESC/Q             : Quit"
