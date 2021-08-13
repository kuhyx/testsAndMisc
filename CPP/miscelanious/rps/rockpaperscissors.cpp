#include <iostream>
#include <vector>

std::vector <std::string> WIN_MESSAGE = {"It's a draw!", "Player One Won!", "Player Two Won!"};

void print(const std::string s)
{
  std::cout << s << std::endl;
}

int playerChoose(const bool playerNumber)
{
  int playerChoice;
  if (playerNumber == 0) print("Player one choose: \n[1] Rock \n[2] Paper \n[3] Scissors");
  else print("Player one choose: \n[1] Rock \n[2] Paper \n[3] Scissors");
  std::cin >> playerChoice;
  return playerChoice;
}

void playerOneWins()
{
  print("Player One Wins!");
}

void playerTwoWins()
{
  print("Player Two Wins!");
}

void draw()
{
  print("It's a draw!");
}

int whoWon(const int playerOneChoice, const int playerTwoChoice)
{
  if( (playerOneChoice == 1 && playerTwoChoice == 3) || (playerOneChoice == 2 && playerTwoChoice == 1) || (playerOneChoice == 3 && playerTwoChoice == 2)) return 1;
  else if(playerOneChoice == playerTwoChoice) return 0;
  else return 2;
}

bool tests()
{
  if(whoWon(1, 1) != 0) return 0;
  if(whoWon(1, 2) != 2) return 0;
  if(whoWon(1, 3) != 1) return 0;
  if(whoWon(2, 1) != 1) return 0;
  if(whoWon(2, 2) != 0) return 0;
  if(whoWon(2, 3) != 2) return 0;
  if(whoWon(3, 1) != 2) return 0;
  if(whoWon(3, 2) != 1) return 0;
  if(whoWon(3, 3) != 0) return 0;
  return 1;
}

int main()
{
  if(!tests())
  {
    print("There is an error in program logic!");
    return -1;
  }
  int playerOneChoice = playerChoose(0);
  int playerTwoChoice = playerChoose(1);
  std::cout << WIN_MESSAGE[whoWon(playerOneChoice, playerTwoChoice)] << std::endl;
  return 0;
}
