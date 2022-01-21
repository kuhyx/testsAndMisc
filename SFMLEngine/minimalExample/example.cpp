// SFML is split into 5 modules:
// #include <SFML/Graphics.hpp>
// #include <SFML/Audio.hpp>
// #include <SFML/System.hpp>
// #include <SFML/Window.hpp>
// #include <SFML/Network.hpp>
// We can include them like this or we can include just a specific header file:
// #include <SFML/Audio/Sound.hpp>
// Each module is compiled to separate library, it can be built for release or debug, linked statically or dynamically

#include <SFML/Graphics.hpp>

int main()
{
  sf::RenderWindow window(sf::VideoMode(640, 480), "SFML Application");
  sf::CircleShape shape;
  const float CIRCLE_RADIUS = 40;
  shape.setRadius(CIRCLE_RADIUS);
  const float CIRCLE_POSITION_X = 100;
  const float CIRCLE_POSITION_Y = 100;
  shape.setPosition(CIRCLE_POSITION_X, CIRCLE_POSITION_Y);
  shape.setFillColor(sf::Color::Cyan);
  while(window.isOpen())
  {
    sf::Event event;
    while(window.pollEvent(event))
    {
      if(event.type == sf::Event::Closed) window.close();
    }
    window.clear();
    window.draw(shape);
    window.display();
  }
}
