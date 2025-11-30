#include <iostream>
#include <vector>

void printField(std::vector<unsigned int> &field)
{
    std::cout << std::endl;
    for(int i = 0; i < 9; i++)
    {
        if(i % 3 == 0) std::cout << std::endl;
        if(field[i] == 0) std::cout << "-";
        else if(field[i] == 1) std::cout << "X";
        else if(field[i] == 2) std::cout << "O";
    }
    std::cout << std::endl;
}


unsigned int chooseField(unsigned int playerNumber, std::vector<unsigned int> &field)
{
    unsigned int chosenField;
    do
    {
        std::cout << "player " << playerNumber << " choose a field:" << std::endl;
        std::cin >> chosenField;
    }while(field[chosenField] != 0);
    return chosenField;
}

bool vertical(unsigned int playerNumber, std::vector<unsigned int> &field)
{
    if((field[0] == playerNumber && field[1] == playerNumber &&  field[2] == playerNumber)
       || (field[3] == playerNumber && field[4] == playerNumber &&  field[5] == playerNumber)
       || (field[6] == playerNumber && field[7] == playerNumber &&  field[8] == playerNumber))
       {
           return 1;
       }else return 0;
}

bool horizontal(unsigned int playerNumber, std::vector<unsigned int> &field)
{
    if((field[0] == playerNumber && field[3] == playerNumber &&  field[6] == playerNumber)
       || (field[1] == playerNumber && field[4] == playerNumber &&  field[7] == playerNumber)
       || (field[2] == playerNumber && field[5] == playerNumber &&  field[8] == playerNumber))
       {
           return 1;
       }else return 0;
}

bool across(unsigned int playerNumber, std::vector<unsigned int> &field)
{
    if((field[0] == playerNumber && field[4] == playerNumber &&  field[8] == playerNumber)
       || (field[2] == playerNumber && field[4] == playerNumber &&  field[6] == playerNumber))
    {
        return 1;
    }else return 0;
}

bool checkPlayerWin(unsigned int playerNumber, std::vector<unsigned int> &field)
{
    if(vertical(playerNumber, field)) return 1;
    if(horizontal(playerNumber, field)) return 1;
    if(across(playerNumber, field)) return 1;
    else return 0;
}

unsigned int checkIfWin(std::vector<unsigned int> &field)
{
    if(checkPlayerWin(1, field)) return 1;
    else if(checkPlayerWin(2, field)) return 2;
    else return 0;
}

bool checkIfFilled(std::vector<unsigned int> &field)
{
    bool filled = 1;
    for(int i = 0; i < 9; i++)
    {
        if(field[i] == 0)
        {
            filled = 0;
            return filled;
        }
    }
    return filled;
}

bool turn(unsigned int playerNumber, std::vector<unsigned int> &field, bool *filled, unsigned int *whoWon)
{
        field[chooseField(playerNumber, field)] = playerNumber;
        printField(field);
        *whoWon = checkIfWin(field);
        *filled = checkIfFilled(field);
        if(*whoWon != 0 || *filled != 0) return 1;
        else return 0;
}

int main()
{
    std::vector<unsigned int> field = {0, 0, 0, 0, 0, 0, 0, 0, 0};
    unsigned int whoWon = 0;
    bool filled = 0;

    while(whoWon == 0 || filled == 0)
    {
        if(turn(1, field, &filled, &whoWon)) break;
        if(turn(2, field, &filled, &whoWon)) break;
    }
    if(!filled) std::cout << "Player " << whoWon << " Won!" << std::endl;
    else std::cout << "DRAW!" << std::endl;
    return 0;
}
