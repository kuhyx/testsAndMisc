CC = gcc
CFLAGS = -Wall -Wextra -std=c23 -O2
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

.PHONY: all clean install deps help lint format check memcheck

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE) $(LIBS)

clean:
	rm -f $(TARGET)

# Linting and code quality targets
lint:
	@echo "Running comprehensive lint checks..."
	@./lint.sh

format:
	@echo "Formatting code..."
	@if command -v clang-format >/dev/null 2>&1; then \
		clang-format -i $(SOURCE); \
		echo "Code formatted successfully"; \
	else \
		echo "clang-format not found. Install it with: sudo pacman -S clang"; \
	fi

check: lint
	@echo "Running extended checks..."
	@if command -v valgrind >/dev/null 2>&1; then \
		echo "Memory leak check available. Run: make memcheck"; \
	else \
		echo "Install valgrind for memory leak detection: sudo pacman -S valgrind"; \
	fi

memcheck: $(TARGET)
	@echo "Running memory leak check..."
	@valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./$(TARGET) 2>&1 | head -50

# Install dependencies on Ubuntu/Debian
deps-debian:
	sudo apt-get update
	sudo apt-get install libsdl2-dev libsdl2-image-dev clang-tidy cppcheck clang-format valgrind

# Install dependencies on Fedora/RHEL/CentOS
deps-fedora:
	sudo dnf install SDL2-devel SDL2_image-devel clang-tools-extra cppcheck clang valgrind

# Install dependencies on Arch Linux
deps-arch:
	sudo pacman -S sdl2 sdl2_image clang cppcheck valgrind

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
	@echo "imageViewer - Makefile targets:"
	@echo "  all          - Build the image viewer"
	@echo "  clean        - Remove built files"
	@echo "  test         - Run with a test image (if available)"
	@echo "  lint         - Run comprehensive code linting"
	@echo "  format       - Format code with clang-format"
	@echo "  check        - Run all code quality checks"
	@echo "  memcheck     - Run memory leak detection"
	@echo "  deps-debian  - Install dependencies on Ubuntu/Debian"
	@echo "  deps-fedora  - Install dependencies on Fedora/RHEL/CentOS"
	@echo "  deps-arch    - Install dependencies on Arch Linux"
	@echo "  help         - Show this help"
	@echo ""
	@echo "Code Quality Workflow:"
	@echo "  1. make lint     - Check for issues"
	@echo "  2. make format   - Fix formatting"
	@echo "  3. make check    - Run all checks"
	@echo "  4. make          - Build project"
	@echo "  5. make memcheck - Check for memory leaks"
	@echo ""
	@echo "Usage: ./$(TARGET) <image_file.jpg>"
