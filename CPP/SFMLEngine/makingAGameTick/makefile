CXXFLAGS = -Wextra -Wall -Wfloat-equal -Wundef -Wshadow -Wpointer-arith -Wcast-align -Wstrict-overflow=5 -Wwrite-strings -Wcast-qual -Wunreachable-code -pedantic -Wswitch-default -Wno-unused-parameter
# https://stackoverflow.com/a/3376483

compile:./game.cpp
	g++ $(CXXFLAGS) -c ./game.cpp
	g++ game.o -o app -lsfml-graphics -lsfml-window -lsfml-system

run:
	./app
