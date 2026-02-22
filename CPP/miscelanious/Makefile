CXX := g++
CXXFLAGS := -O2 -Wall -Wextra -std=c++17
LDFLAGS :=

BINS := howOftenDoesCharOccur quickchallenges reverseString solveQuadraticEquation

all: $(BINS)

howOftenDoesCharOccur: howOftenDoesCharOccur.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

quickchallenges: quickchallenges.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

reverseString: reverseString.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

solveQuadraticEquation: solveQuadraticEquation.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

run: all
	./howOftenDoesCharOccur
	./quickchallenges
	./reverseString
	./solveQuadraticEquation

clean:
	rm -f $(BINS)

.PHONY: all run clean
