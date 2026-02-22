// Optimized ISBN-10 counter.
//
// Three improvements over the original:
//
// 1. NO HEAP ALLOCATION — original calls intToVector() on every iteration,
//    which does a heap alloc+free (std::vector) for each of 10^10 numbers.
//    Here we use only stack variables.
//
// 2. ALGORITHMIC REDUCTION — ISBN-10 validity condition:
//    10*d0 + 9*d1 + ... + 2*d8 + 1*d9 ≡ 0  (mod 11)
//    Given any 9-digit prefix d0..d8 we can solve for d9 directly:
//    d9 = (11 - S mod 11) mod 11   where S = sum of weighted prefix
//    The number is valid iff 0 ≤ d9 ≤ 9 (i.e. d9 ≠ 10).
//    → Only 10^9 outer iterations instead of 10^10.
//
// 3. INCREMENTAL WEIGHTED SUM — instead of multiplying each digit by its
//    weight inside the innermost loop, partial sums are maintained
//    incrementally as digits change, so the innermost body is almost free.
//    The compiler can also vectorise the innermost digit loop.
//
// Compile: g++ -O2 -fopenmp bench_optimized.cpp -o bench_opt
// (OpenMP is optional; remove -fopenmp if not available – it just runs
//  the outer loop on a single thread.)

#include <chrono>
#include <iostream>

#ifdef _OPENMP
#include <omp.h>
#endif

int main() {
  auto start = std::chrono::high_resolution_clock::now();

  long long count = 0;

  // Nested loops over the 9 prefix digits.
  // s_k = partial weighted sum up through digit k.
  //       weight for digit at position i (0-based, MSB first) = 10 - i
  //       so outer digit d0 has weight 10, d1 has weight 9, ..., d8 has
  //       weight 2.

#ifdef _OPENMP
#pragma omp parallel for reduction(+ : count) schedule(static)
#endif
  for (int d0 = 0; d0 <= 9; d0++) {
    int s0 = 10 * d0;
    for (int d1 = 0; d1 <= 9; d1++) {
      int s1 = s0 + 9 * d1;
      for (int d2 = 0; d2 <= 9; d2++) {
        int s2 = s1 + 8 * d2;
        for (int d3 = 0; d3 <= 9; d3++) {
          int s3 = s2 + 7 * d3;
          for (int d4 = 0; d4 <= 9; d4++) {
            int s4 = s3 + 6 * d4;
            for (int d5 = 0; d5 <= 9; d5++) {
              int s5 = s4 + 5 * d5;
              for (int d6 = 0; d6 <= 9; d6++) {
                int s6 = s5 + 4 * d6;
                for (int d7 = 0; d7 <= 9; d7++) {
                  int s7 = s6 + 3 * d7;
                  // Innermost: vary d8, weight 2.
                  for (int d8 = 0; d8 <= 9; d8++) {
                    int s = s7 + 2 * d8;
                    // Required check digit (weight 1):
                    int d9 = (11 - s % 11) % 11;
                    if (d9 <= 9)
                      ++count;
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  auto end = std::chrono::high_resolution_clock::now();
  double elapsed = std::chrono::duration<double>(end - start).count();

  std::cout << "Valid ISBNs: " << count << "\n";
  std::cout << "Time:        " << elapsed << " s\n";

#ifdef _OPENMP
  std::cout << "Threads:     " << omp_get_max_threads() << "\n";
#endif

  return 0;
}
