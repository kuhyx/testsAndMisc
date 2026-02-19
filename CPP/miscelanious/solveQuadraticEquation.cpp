#include <iostream>
#include <math.h>
#include <string>

const std::string ENTER = "Enter quadratic equation constants: ";
const std::string WHAT_TO_INPUT = "a, b, c as in: ax^2 + bx + c = 0";
const std::string START = ENTER + WHAT_TO_INPUT;

void print(const std::string s) { std::cout << s << std::endl; }

float getDelta(float a, float b, float c) { return b * b - 4 * a * c; }

float calculateFirstTerm(float a, float b, float delta) {
  return (-b - sqrt(delta)) / (2 * a);
}

float calculateSecondTerm(float a, float b, float delta) {
  return (-b + sqrt(delta)) / (2 * a);
}

int main() {
  print(START);
  float a, b, c;
  std::cin >> a;
  std::cin >> b;
  std::cin >> c;
  float delta = getDelta(a, b, c);
  if (delta < 0) {
    print("delta smaller than 0");
    return -1;
  }

  float x_1 = calculateFirstTerm(a, b, delta);
  float x_2 = calculateSecondTerm(a, b, delta);
  print("Solutions:");
  std::cout << "x_1 = " << x_1 << std::endl;
  std::cout << "x_2 = " << x_2 << std::endl;
  return 0;
}
