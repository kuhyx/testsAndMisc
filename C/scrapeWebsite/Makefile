# Compiler
CC = gcc

# Compiler flags
CFLAGS = -Wall -O3 -march=native -I/usr/include/libxml2

# Libraries
LIBS = -lcurl -lxml2

# Source files
SRCS = scrape.c

# Output executable
TARGET = scrape

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
