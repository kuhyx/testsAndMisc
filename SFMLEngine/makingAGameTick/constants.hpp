#ifndef CONSTANTS_HPP
#define CONSTANTS_HPP

#include <SFML/Graphics.hpp>

// Paths
const std::string PATH_TO_PLAYER_TEXTURE = "Textures/Player.png";
const std::string PATH_TO_EAGLE_TEXTURE = "Textures/Eagle.png";
const std::string PATH_TO_RAPTOR_TEXTURE = "Textures/Raptor.png";
const std::string PATH_TO_DESERT_TEXTURE = "Textures/Desert.jpg";

// Player constants
const float PLAYER_RADIUS = 40;
const float PLAYER_X_POSITION = 100;
const float PLAYER_Y_POSITION = 100;
const sf::Color PLAYER_COLOR = sf::Color::Cyan;
const float PLAYER_SIDEWARD_VELOCITY = 40;

// Other sprites constants
const float LEFT_ESCORT_X_POSITION = -80;
const float LEFT_ESCORT_Y_POSITION = 50;
const float RIGHT_ESCORT_X_POSITION = -LEFT_ESCORT_X_POSITION;
const float RIGHT_ESCORT_Y_POSITION = LEFT_ESCORT_Y_POSITION;

// Movement constants
// const sf::Vector2f INITIAL_MOVEMENT (0.f, 0.f);

const float MOVING_UP_SPEED = -100;
const float MOVING_DOWN_SPEED = -MOVING_UP_SPEED;
const float MOVING_RIGHT_SPEED = 100;
const float MOVING_LEFT_SPEED = -MOVING_RIGHT_SPEED;

// Time constants
const sf::Time TIME_PER_FRAME = sf::seconds(1.f / 60.f); // 1 frame is 1 / 60 of the second so we get 60 frames in a second

// Error strings
const std::string TEXTURE_LOAD_ERROR = "TextureHolder::load - Failed to load ";

// World constants
const float WORLD_LEFT_X_POSITION = 0;
const float WORLD_TOP_Y_POSITION = 0;
// const float WORLD_WIDTH = 0; by default mWorldView.getSize().x
const float WORLD_HEIGHT = 2000;
const float WORLD_SCROLL_SPEED = -1;
const float WORLD_MAX_DISTANCE_FROM_BOUNDARY = 150;

#endif // CONSTANTS_HPP
