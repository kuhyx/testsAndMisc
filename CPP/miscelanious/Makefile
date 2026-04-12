CXX      := g++
CXXFLAGS := -O2 -Wall -Wextra -std=c++17
LDFLAGS  :=

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

# ---- Coverage build: separate compilation so gcov data is per source file ----
COV := -O2 -g --coverage -Wall -Wextra -std=c++17 -DTESTING

howOftenDoesCharOccur.o: howOftenDoesCharOccur.cpp
	$(CXX) $(COV) -c -o $@ $<

quickchallenges.o: quickchallenges.cpp
	$(CXX) $(COV) -c -o $@ $<

reverseString.o: reverseString.cpp
	$(CXX) $(COV) -c -o $@ $<

solveQuadraticEquation.o: solveQuadraticEquation.cpp
	$(CXX) $(COV) -c -o $@ $<

test_challenges.o: test_challenges.cpp
	$(CXX) $(COV) -c -o $@ $<

TEST_OBJS := test_challenges.o howOftenDoesCharOccur.o quickchallenges.o reverseString.o solveQuadraticEquation.o

test_challenges: $(TEST_OBJS)
	$(CXX) -O2 -g --coverage -o $@ $^

test: test_challenges
	./test_challenges

coverage: test_challenges
	./test_challenges
	lcov --capture --directory . --output-file coverage.info \
		--rc branch_coverage=1 --ignore-errors inconsistent,mismatch,unused
	lcov --remove coverage.info '/usr/*' --output-file coverage.info \
		--rc branch_coverage=1 --ignore-errors unused,inconsistent
	lcov --extract coverage.info \
		"$(CURDIR)/howOftenDoesCharOccur.cpp" \
		"$(CURDIR)/quickchallenges.cpp" \
		"$(CURDIR)/reverseString.cpp" \
		"$(CURDIR)/solveQuadraticEquation.cpp" \
		--output-file coverage.info \
		--ignore-errors unused,inconsistent
	@echo "--- Coverage Summary ---"
	lcov --summary coverage.info --rc branch_coverage=1 2>&1 | tee /tmp/lcov_summary.txt
	@LINE_COV=$$(grep "lines" /tmp/lcov_summary.txt | grep -oP '[0-9]+\.[0-9]+(?=%)'); \
	echo "Line coverage: $${LINE_COV}%"; \
	if [ "$$(echo "$${LINE_COV} < 100.0" | bc)" = "1" ]; then \
		echo "FAIL: line coverage below 100%"; exit 1; \
	fi
	@echo "OK: 100% line coverage achieved"

run: all
	./howOftenDoesCharOccur
	./quickchallenges
	./reverseString
	./solveQuadraticEquation

clean:
	rm -f $(BINS) test_challenges *.gcda *.gcno *.gcov coverage.info *.o

.PHONY: all run clean test coverage
