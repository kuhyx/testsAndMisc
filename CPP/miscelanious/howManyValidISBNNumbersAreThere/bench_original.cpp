// Benchmark version of the original algorithm.
// File I/O removed so we measure pure computation time.
#include <algorithm>
#include <chrono>
#include <iostream>
#include <vector>

const int ISBN_LENGTH = 10;
const int CHECK_NUMBER = 11;
const unsigned long long int HIGHEST_ISBN = 9999999999ULL;

bool checkISBN(const std::vector<int> isbn) {
  int sum = 0, t = 0;
  for (int i = 0; i < ISBN_LENGTH; i++) {
    t += isbn[i];
    sum += t;
  }
  return !(sum % CHECK_NUMBER);
}

std::vector<int> intToVector(unsigned long long int number) {
  std::vector<int> numbers;
  while (number > 0) {
    numbers.push_back(number % 10);
    number /= 10;
  }
  std::reverse(numbers.begin(), numbers.end());
  return numbers;
}

// Run for at most SAMPLE seconds, then extrapolate total time.
static constexpr double SAMPLE_SECS = 20.0;

long long checkAllTimed(double &elapsed_out) {
  auto start = std::chrono::high_resolution_clock::now();
  auto limit = start + std::chrono::duration<double>(SAMPLE_SECS);
  long long sum = 0;
  unsigned long long i;
  for (i = HIGHEST_ISBN; i >= 1; i--) {
    if (checkISBN(intToVector(i)))
      ++sum;

    // Check wall-clock every 1 million iterations to keep overhead low.
    if ((i & 0xFFFFF) == 0) {
      if (std::chrono::high_resolution_clock::now() >= limit)
        break;
    }
  }
  auto end = std::chrono::high_resolution_clock::now();
  elapsed_out = std::chrono::duration<double>(end - start).count();

  unsigned long long done = HIGHEST_ISBN - i;
  double rate = (double)done / elapsed_out; // numbers/s
  double total_est = (double)HIGHEST_ISBN / rate;

  std::cout << "Iterated:      " << done << " numbers in " << elapsed_out
            << " s\n";
  std::cout << "Rate:          " << (long long)rate << " numbers/s\n";
  std::cout << "Estimated total time for full range: " << (long long)total_est
            << " s  (" << total_est / 60.0 << " min)\n";
  return sum;
}

int main() {
  double elapsed = 0.0;
  long long count = checkAllTimed(elapsed);
  std::cout << "Valid ISBNs in sampled range: " << count << "\n";
  return 0;
}
