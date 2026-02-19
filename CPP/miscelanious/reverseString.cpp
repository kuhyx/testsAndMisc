#include <algorithm>
#include <iostream>
#include <string>

int main() {
  std::string userString;
  getline(std::cin, userString);
  int sLength = userString.length();
  std::string tempString = userString;
  for (int i = 0; i < sLength / 2; i++) {
    char temp = tempString[sLength - 1 - i];
    tempString[sLength - 1 - i] = tempString[i];
    tempString[i] = temp;
  }
  reverse(userString.begin(), userString.end());
  bool correct = tempString == userString;
  std::cout << correct << std::endl;
  std::cout << tempString << std::endl;
  return 0;
}
