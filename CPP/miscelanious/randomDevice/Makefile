CXX := g++
CXXFLAGS := -O2 -Wall -Wextra -std=c++17
LDFLAGS :=

SRC := main.cpp
BIN := random_device_demo

all: $(BIN)

$(BIN): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
