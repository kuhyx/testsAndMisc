#include <vector>
#include <SFML/Graphics.hpp>
#include "constants.hpp"
#include "basic.cpp"

class Game
{
  public:
    Game(); // Sets up player radius, position and fill color
    void run(); // runs the processEvents, update and render methods

  private:
    void processEvents(); // playerInput, mainLoop
    void update(); // code that updates the game
    void render(); // code that renders the game
    void handlePlayerInput(sf::Keyboard::Key key, bool isPressed);
    bool mIsMovingUp = false;
    bool mIsMovingRight = false;
    bool mIsMovingLeft = false;
    bool mIsMovingDown = false;
  private:
    sf::RenderWindow mWindow;
    sf::CircleShape mPlayer;
};

Game::Game() : mWindow(sf::VideoMode(640, 480), "SFML Application"), mPlayer()
{
  mPlayer.setRadius(PLAYER_RADIUS);
  mPlayer.setPosition(PLAYER_X_POSITION, PLAYER_Y_POSITION);
  mPlayer.setFillColor(PLAYER_COLOR);
}

void Game::run()
{
  while (mWindow.isOpen())
  {
    processEvents();
    update();
    render();
  }
}

/*
const std::vector < pair<bool, sf::Keyboard::Key> > PLAYER_MOVEMENT =
{
  {mIsMovingUp, sf::Keyboard::W},
  {mIsMovingDown, sf::Keyboard::S},
  {mIsMovingLeft, sf::Keyboard::A},
  {mIsMovingRight, sf::Keyboard::D}
}
*/

void Game::handlePlayerInput(sf::Keyboard::Key key, bool isPressed)
{
  if (key == sf::Keyboard::W) mIsMovingUp = isPressed;
  else if (key == sf::Keyboard::S) mIsMovingDown = isPressed;
  else if (key == sf::Keyboard::A) mIsMovingLeft = isPressed;
  else if (key == sf::Keyboard::D) mIsMovingRight = isPressed;
}

void Game::processEvents()
{
  sf::Event event;
  while (mWindow.pollEvent(event)) // mainLoop/gameLoop
  {
    // each time while loop iterates it means that we got a new event registered by the window.
    switch (event.type)
    {
      case sf::Event::KeyPressed:
        handlePlayerInput(event.key.code, true);
        break;
      case sf::Event::KeyReleased:
        handlePlayerInput(event.key.code, false);
        break;
      case sf::Event::Closed:
        mWindow.close();
        break;
    }
  }
}

void Game::update()
{

  sf::Vector2f movement (0.f, 0.f);
  movement.y += mIsMovingUp * MOVING_UP_SPEED + mIsMovingDown * MOVING_DOWN_SPEED;
  movement.x += mIsMovingLeft * MOVING_LEFT_SPEED + mIsMovingRight * MOVING_RIGHT_SPEED;
  mPlayer.move(movement);

}

void Game::render()
{
  mWindow.clear();
  mWindow.draw(mPlayer);
  mWindow.display();
}

int main()
{
  Game game;
  game.run();
}
