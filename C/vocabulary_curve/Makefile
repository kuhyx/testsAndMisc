CC = gcc
CFLAGS = -O3 -Wall -Wextra -march=native
TARGET = vocabulary_curve

all: $(TARGET)

$(TARGET): main.c
	$(CC) $(CFLAGS) -o $(TARGET) main.c

clean:
	rm -f $(TARGET)

.PHONY: all clean
