#ifndef ENTITY_HPP
#define ENTITY_HPP

class Entity
{
public:
  void SetVelocity(sf::Vector2f velocity);
  void setVelocity(float velocityX, float velocityY);
  sf::Vector2f getVelocity() const;

  private:
  sf::Vector2f mVelocity; // default ocnstructor initializes this vector to a zero vector

};

#include "entity.cpp"

#endif
