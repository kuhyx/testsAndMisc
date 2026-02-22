CXX := g++
CXXFLAGS := -O2 -Wall -Wextra -std=c++17
LDFLAGS := -lm

SRC := main.cpp
BIN := pi

all: $(BIN)

$(BIN): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
