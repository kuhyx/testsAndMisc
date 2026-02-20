#include <iostream>
#include <string>
#include <vector>

const std::vector<std::string> TIERS = {"Abhorrent", "Bad", "Mid",
                                        "Good",      "Top", "God Tier"};
const float TIER_BASE = TIERS.size();

void print(std::string const s) { std::cout << s << std::endl; }

bool errorUserInput(std::string userInput) {
  if (userInput.find("/") == std::string::npos) {
    print("No '/' was found!");
    return 1;
  }

  size_t positionOfSlash = userInput.find("/");
  std::string nominatorS = userInput.substr(0, positionOfSlash);

  try {
    float nominator = stof(nominatorS);
  } catch (std::invalid_argument) {
    print("No number was found before the slash!");
    return 1;
  }

  std::string denominatorS =
      userInput.substr(positionOfSlash + 1, userInput.length() - 1);

  try {
    float denominator = stof(denominatorS);
    if (denominator == 0) {
      print("You cannot divide by 0!");
      return 1;
    }
  } catch (std::invalid_argument) {
    print("No number was found after the slash!");
    return 1;
  }

  return 0;
}

std::string convertToTier(float nominator, float denominator) {
  float fraction = nominator / denominator;
  int tierIndex = 0;
  for (int i = TIER_BASE; i > 0; i--) {
    if (fraction >= (i / TIER_BASE)) {
      tierIndex = i - 1;
      break;
    }
  }
  if (tierIndex == 0 && fraction > (1.1 / 10.0))
    return TIERS[1];
  return TIERS[tierIndex];
}

int main() {
  std::string userScore;
  do {
    print("Enter your score in a format: numberOne/numberTwo");
    getline(std::cin, userScore);
  } while (errorUserInput(userScore));

  size_t positionOfSlash = userScore.find("/");
  std::string nominatorS = userScore.substr(0, positionOfSlash);

  float nominator = stof(nominatorS);
  std::string denominatorS =
      userScore.substr(positionOfSlash + 1, userScore.length() - 1);

  float denominator = stof(denominatorS);
  print(convertToTier(nominator, denominator));
  return 0;
}
