#ifndef CONSTANTS_HPP
#define CONSTANTS_HPP

#include <SFML/Graphics.hpp>

// Player constants
const float PLAYER_RADIUS = 40;
const float PLAYER_X_POSITION = 100;
const float PLAYER_Y_POSITION = 100;
const sf::Color PLAYER_COLOR = sf::Color::Cyan;

// Movement constants
// const sf::Vector2f INITIAL_MOVEMENT (0.f, 0.f);
const float MOVING_UP_SPEED = -1;
const float MOVING_DOWN_SPEED = -MOVING_UP_SPEED;
const float MOVING_RIGHT_SPEED = 1;
const float MOVING_LEFT_SPEED = -MOVING_RIGHT_SPEED;

#endif // CONSTANTS_HPP
