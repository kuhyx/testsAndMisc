#include "reverseString.h"
#include <algorithm>
#include <iostream>
#include <string>

std::string reverseStringManual(const std::string &s) {
  std::string result = s;
  int sLength = static_cast<int>(result.length());
  for (int i = 0; i < sLength / 2; i++) {
    char temp = result[sLength - 1 - i];
    result[sLength - 1 - i] = result[i];
    result[i] = temp;
  }
  return result;
}

#ifndef TESTING
int main() {
  std::string userString;
  getline(std::cin, userString);
  std::string tempString = reverseStringManual(userString);
  std::string stdReversed = userString;
  reverse(stdReversed.begin(), stdReversed.end());
  bool correct = tempString == stdReversed;
  std::cout << correct << std::endl;
  std::cout << tempString << std::endl;
  return 0;
}
#endif
