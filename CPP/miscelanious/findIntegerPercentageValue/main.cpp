#include <iostream>
#include <cmath>

const int PERCENTAGE = 44;
const float PERCENTAGE_DENOMINATOR = 100;
const int NUMBERS_TO_CHECK = 200;
const bool DEBUG = 0;

bool isInteger(const float number)
{
	return number == std::floor(number);
}

void printIsInteger(const int i, const int inputPercentage,
					const float calculatedPercentage)
{
	std::cout << i << "*" << inputPercentage << "% is an integer number: "
	<< i*calculatedPercentage << std::endl;
}

void printDebug(const int i, const float calculatedPercentage)
{
	std::cout << "i = " << i << std::endl;
	std::cout << i*calculatedPercentage << std::endl;
}

void isIntegerLoop(	const bool debugOn = DEBUG,
					const int maxNumber = NUMBERS_TO_CHECK,
					const int inputPercentage = PERCENTAGE	)
{
	float actualPercentage = inputPercentage / PERCENTAGE_DENOMINATOR;
	for(int i = 1; i <= maxNumber; i++)
	{
		if(isInteger(i*actualPercentage))
		{
			printIsInteger(i, inputPercentage, actualPercentage);
		}
		else if(debugOn) printDebug(i, actualPercentage);
	}
}

void printStartingMessage(const int maxNumber = NUMBERS_TO_CHECK,
					const int inputPercentage = PERCENTAGE)
{
	std::cout << "For max number = " << maxNumber
	<< "; and a percentage: " <<  inputPercentage
	<< "; Found following integer numbers: " << std::endl;
}

void mainFunctions()
{
	printStartingMessage();
	isIntegerLoop();
}

int main()
{
	mainFunctions();
	return 0;
}
