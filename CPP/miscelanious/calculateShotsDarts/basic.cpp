#ifndef BASIC_CPP
#define BASIC_CPP

#include <iostream>
#include <string>
#include <vector>
#include <windows.h>

void print(const std::string s) { std::cout << s << std::endl; }
void printErrorStringContainsNotNumber(const std::string s) {
  std::cout << "string: \"" << s
            << "\" contains character different than number " << std::endl;
}

void printNumberTooLow(const int number, const int min) {
  std::cout << "number: " << number << " is too low. Minimal number is: " << min
            << std::endl;
}

void printNumberTooHigh(const int number, const int max) {
  std::cout << "number: " << number
            << " is too high. Maximal number is: " << max << std::endl;
}

void printNotValidStringLength(const std::string s, const int desiredLength) {
  std::cout << "String: \"" << s
            << "\" is too short/too long, it is: " << s.length()
            << " characters long but should be: " << desiredLength
            << " characters long " << std::endl;
}

void printInvalidCharacter(const char c, const char desiredCharacter) {
  std::cout << "[ " << c << " ] Is invalid character, expected: [ "
            << desiredCharacter << " ]" << std::endl;
}

void printContainsIllegalCharacter(const std::string s,
                                   const char illegalCharacter) {
  std::cout << "String: " << s << " consists of illegal sign: ["
            << illegalCharacter << "]!" << std::endl;
}

bool numberTooLow(const int number, const int min) {
  if (number < min) {
    printNumberTooLow(number, min);
    return 1;
  }
  return 0;
}

bool numberTooHigh(const int number, const int max) {
  if (number > max) {
    printNumberTooHigh(number, max);
    return 1;
  }
  return 0;
}

bool containsIllegalCharacter(const std::string s,
                              const char illegalCharacter) {
  if (s.find(illegalCharacter) != std::string::npos) {
    printContainsIllegalCharacter(s, illegalCharacter);
    return 1;
  }
  return 0;
}

void e() { print("Poor man breakboint"); }

bool charIsNumber(const char c) { return c >= '0' && c <= '9'; }

#endif
