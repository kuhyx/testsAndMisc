#include <iomanip>
#include <iostream>
#include <math.h>

const unsigned long long int ITERATIONS = 10000;

long double getPi() {
  long double pi = 4;
  bool negative = 1;
  for (unsigned int i = 3; i < ITERATIONS; i += 2) {
    if (negative)
      pi -= 4.0 / i;
    else
      pi += 4.0 / i;
    negative = !negative;
  }
  std::cout << std::setprecision(2000) << pi << std::endl;
  return pi;
}

int main() {
  getPi();
  return 0;
}
