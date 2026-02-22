#include <algorithm>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

#ifndef CHECK_ISBN_CPP
#define CHECK_ISBN_CPP

const bool DEBUG = 0;
const int ISBN_LENGTH = 10;
const int CHECK_NUMBER = 11;
const unsigned long long int HIGHEST_ISBN = 9999999999;

void printVector(std::vector<int> v) {
  for (unsigned int i = 0; i < v.size(); i++) {
    std::cout << v[i] << "; ";
  }
}

void print(const std::string printMe) { std::cout << printMe << std::endl; }

void e() { print("PRINT"); }

bool checkInput(const std::string input) {
  if (input.length() != ISBN_LENGTH) {
    print("Your number is too short/too long");
    return 0;
  }
  for (int i = 0; i <= ISBN_LENGTH - 1; i++) {
    if (input.at(i) < '0' || input.at(i) > '9') {
      print("Your number consists of illegal characters");
      return 0;
    }
  }
  return 1;
}

std::vector<int> stringToIntVector(const std::string input) {
  std::vector<int> vector;
  for (int i = input.length() - 1; i >= 0; i--) {
    vector.push_back(input.at(i) - '0');
  }
  return vector;
}

std::vector<int> userISBN() {
  std::string input;
  do {
    std::cout << "Enter the ISBN number (10 digits): ";
    getline(std::cin, input);
  } while (!checkInput(input));
  return stringToIntVector(input);
}

bool checkISBN(const std::vector<int> isbn) {
  int sum = 0, t = 0;
  for (int i = 0; i < ISBN_LENGTH; i++) {
    t += isbn[i];
    sum += t;
  }

  /*if(DEBUG)
  {
          if(!(sum % CHECK_NUMBER)) print("^^^ VALID NUMBER ^^^");
  } */

  return !(sum % CHECK_NUMBER);
}

// Optimisation 1 – no heap allocation: intToVector() removed; checkAll()
//   uses only stack variables in the nested loops below.
//
// Optimisation 2 – algorithmic reduction (10^10 → 10^9 iterations):
//   ISBN-10 validity: 10*d0 + 9*d1 + ... + 2*d8 + 1*d9 ≡ 0  (mod 11)
//   Given a 9-digit prefix d0..d8 the check digit is determined:
//     d9 = (11 - S%11) % 11   where S = weighted sum of prefix
//   The number is valid iff d9 ≤ 9 (i.e. d9 ≠ 10).
//
// Optimisation 3 – incremental partial sums + OpenMP:
//   Each loop level accumulates its contribution once, not inside the
//   innermost body.  The outermost loop is parallelised with OpenMP.
//
// Optimisation 4 – separated I/O:
//   File writing is done in a second serial pass with a large buffer so
//   it doesn't contend with (or race against) the parallel counting pass.
long long countISBNs() {
  long long sum = 0;

#ifdef _OPENMP
#pragma omp parallel for reduction(+ : sum) schedule(static)
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
                  for (int d8 = 0; d8 <= 9; d8++) {
                    int d9 = (11 - (s7 + 2 * d8) % 11) % 11;
                    if (d9 <= 9)
                      ++sum;
                  }
                }
              }
            }
          }
        }
      }
    }
  }
  return sum;
}

void writeISBNsToFile() {
  static const int BUF = 1 << 20; // 1 MB write buffer
  std::ofstream file;
  file.rdbuf()->pubsetbuf(nullptr, BUF);
  file.open("ISBN.txt");
  long long written = 0;

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
                  for (int d8 = 0; d8 <= 9; d8++) {
                    int s = s7 + 2 * d8;
                    int d9 = (11 - s % 11) % 11;
                    if (d9 <= 9) {
                      long long isbn = (long long)d0 * 1000000000LL +
                                       d1 * 100000000 + d2 * 10000000 +
                                       d3 * 1000000 + d4 * 100000 + d5 * 10000 +
                                       d6 * 1000 + d7 * 100 + d8 * 10 + d9;
                      file << isbn << '\n';
                      ++written;
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
  file << "There are " << written << " valid ISBN numbers\n";
  file.close();
}

int main() {
  long long count = countISBNs();
  std::cout << "There are " << count << " valid ISBN numbers\n";
  writeISBNsToFile();
  return 0;
}

#endif
