#include "howOftenDoesCharOccur.h"
#include <iostream>
#include <vector>

void printCharOccurenceVector(const std::vector<charOccurence> v) {
  std::cout << "[";
  for (unsigned int i = 0; i < v.size(); i++) {
    std::cout << "(\"" << v.at(i).c << "\", " << v.at(i).occurrence << ")"
              << (i + 1 == v.size() ? "" : ", ");
  }
  std::cout << "]" << std::endl;
}

std::vector<charOccurence> computeCharOccurences(const std::string &userInput) {
  std::vector<charOccurence> list;
  if (!userInput.empty()) {
    charOccurence newCharOccurence;
    newCharOccurence.c = userInput.at(0);
    newCharOccurence.occurrence = 1;
    for (unsigned int i = 1, j = 1; i < userInput.length(); i++) {
      char newCharacter = userInput.at(i);
      if (newCharacter != newCharOccurence.c) {
        list.push_back(newCharOccurence);
        j = 1;
        newCharOccurence.c = newCharacter;
        newCharOccurence.occurrence = j;
      } else {
        newCharOccurence.occurrence++;
      }
    }
    list.push_back(newCharOccurence);
  }
  auto result = list;
  return result;
}

#ifndef TESTING
int main() {
  std::string userInput = "aaaabbbcca";
  std::vector<charOccurence> list = computeCharOccurences(userInput);
  printCharOccurenceVector(list);
  return 0;
}
#endif
