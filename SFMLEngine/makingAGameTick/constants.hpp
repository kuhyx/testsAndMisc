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
const float MOVING_UP_SPEED = -100;
const float MOVING_DOWN_SPEED = -MOVING_UP_SPEED;
const float MOVING_RIGHT_SPEED = 100;
const float MOVING_LEFT_SPEED = -MOVING_RIGHT_SPEED;

// Time constants
const sf::Time TIME_PER_FRAME = sf::seconds(1.f / 60.f); // 1 frame is 1 / 60 of the second so we get 60 frames in a second

#endif // CONSTANTS_HPP
