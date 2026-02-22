CXX := g++
CXXFLAGS := -O2 -Wall -Wextra -std=c++17
LDFLAGS :=

# main.cpp includes basic.cpp directly
SRC := main.cpp
BIN := markov

all: $(BIN)

$(BIN): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

run: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all run clean
