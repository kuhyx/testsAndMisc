#pragma once
#include <string>
#include <vector>

struct charOccurence {
  char c;
  int occurrence;
};

void printCharOccurenceVector(const std::vector<charOccurence> v);
std::vector<charOccurence> computeCharOccurences(const std::string &userInput);
