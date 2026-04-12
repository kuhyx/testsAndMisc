CC      = gcc
CFLAGS  = -O3 -Wall -Wextra -march=native
COV     = -O0 -g --coverage -Wall -Wextra
TARGET  = vocabulary_curve

all: $(TARGET)

$(TARGET): main.c vocabulary.c vocabulary.h
	$(CC) $(CFLAGS) -o $(TARGET) main.c vocabulary.c

# ---- tests ---------------------------------------------------------------

test_vocabulary: test_vocabulary.c vocabulary.c vocabulary.h
	$(CC) $(COV) -o test_vocabulary test_vocabulary.c vocabulary.c

test: test_vocabulary
	./test_vocabulary

# ---- coverage ------------------------------------------------------------

coverage: test_vocabulary
	./test_vocabulary
	lcov --capture --directory . --output-file coverage.info \
		--rc branch_coverage=1 --ignore-errors inconsistent,mismatch,unused
	lcov --extract coverage.info "$(CURDIR)/vocabulary.c" \
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

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET) test_vocabulary *.gcda *.gcno *.gcov coverage.info

.PHONY: all run clean test coverage
