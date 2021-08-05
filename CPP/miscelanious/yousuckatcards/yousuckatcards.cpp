#include <iostream>
#include <random>
#include <string>

const int SEQUENCE_LENGTH = 3;

const bool BOT_WON = 0;
const bool PLAYER_WON = 1;
const int NOBODY_WON = 2;

void print(std::string const s)
{
    std::cout << s << std::endl;
}

bool validSequence(std::string const s)
{
    if(s.size() != SEQUENCE_LENGTH)
    {
        print("Sequence too long");
        return false;
    }
    if( (s[0] != 'B' && s[0] != 'R') ||
       (s[1] != 'B' && s[1] != 'R') ||
       (s[2] != 'B' && s[2] != 'R'))
       {
           print("Sequence consists of illegal signs!");
           return false;
       }
    return true;
}

std::string playerChoice()
{
    std::string playerSequence;
    do
    {
        std::cin >> playerSequence;
    }
    while(!validSequence(playerSequence));
    return playerSequence;
}

std::string botChoice(std::string  const playerSequence)
{
    std::string botSequence;
    if(playerSequence[1] == 'B') botSequence.push_back('R');
    else botSequence.push_back('B');
    botSequence.push_back(playerSequence[0]);
    botSequence.push_back(playerSequence[2]);
    return botSequence;
}

int compareGeneratedAndPlayers(std::string playerSequence, std::string botSequence, std::string generatedSequence)
{
	int generatedSequenceLength = generatedSequence.length();
	std::string sequenceToCompare = generatedSequence.substr(generatedSequenceLength - SEQUENCE_LENGTH, generatedSequenceLength);
	if(sequenceToCompare.compare(playerSequence) == 0) return PLAYER_WON;
	if(sequenceToCompare.compare(botSequence) == 0) return BOT_WON;
	else return NOBODY_WON;
}

bool game(std::string playerSequence, std::string botSequence)
{
	std::string generatedSequence;
	std::random_device rd;
	std::mt19937 gen(rd());
	std::bernoulli_distribution distribution(0.5);
    for(int i = 0; i < SEQUENCE_LENGTH; i++)
    {
        if(distribution(gen)) generatedSequence.push_back('R');
        else  generatedSequence.push_back('B');
    }
    
    while(compareGeneratedAndPlayers(playerSequence, botSequence, generatedSequence) == NOBODY_WON)
    {
    	if(distribution(gen)) generatedSequence.push_back('R');
        else  generatedSequence.push_back('B');
    }
    
    print(generatedSequence);
	if(compareGeneratedAndPlayers(playerSequence, botSequence, generatedSequence) == PLAYER_WON) return PLAYER_WON;
	else return BOT_WON;
}

void score(int playerWins, int botWins)
{
	std::cout << "Player won: " << playerWins << " times!" << std::endl;
	std::cout << "Bot won: " << botWins << " times!" << std::endl;
}



int main()
{
	int playerWins = 0;
	int botWins = 0;
    do
    {
        print("Do you want to play the game? 1 - yes, 0 - no");
        bool continue_ = 1;
        std::string playerInput;
        std::cin >> playerInput;
        if(playerInput[0] == '1') continue_ = 1;
        else continue_ = 0;
        if(!continue_) break;
        std::string playerSequence;
        print("Write three colors sequence created from 52 cards from the deck (26 Black, 26 Red), write B for Black and R for Red");
        playerSequence = playerChoice();
        std::string botSequence = botChoice(playerSequence);
        print("Bot has chosen this sequence:");
        print(botSequence);
        if(game(playerSequence, botSequence)) 
        {
        	print("You won!");
        	playerWins++;
        	score(playerWins, botWins);
        }
        else 
        {
        	print("Bot won!");
        	botWins++;
        	score(playerWins, botWins);
        }
    }while(1);
    return 1;
}
