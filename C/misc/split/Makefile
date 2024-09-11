# Compiler
CC = gcc

# Compiler flags
CFLAGS = -Wall -O3 -march=native -flto -fomit-frame-pointer

# Libraries
LIBS = -ljpeg

# Source files
SRCS = main.c

# Output executable
TARGET = split

# Default target
all: $(TARGET)

# Link and compile the program
$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRCS) $(LIBS)

# Clean up build artifacts
clean:
	rm -f $(TARGET)

# Install the program (optional)
install: $(TARGET)
	install -m 755 $(TARGET) /usr/local/bin/

.PHONY: all clean install
