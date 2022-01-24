#ifndef ENTITY_HPP
#define ENTITY_HPP
#include "SceneNode.hpp"
#include "SceneNode.cpp"

class Entity : public SceneNode
{
  public:
    void SetVelocity(sf::Vector2f velocity);
    void setVelocity(float velocityX, float velocityY);
    sf::Vector2f getVelocity() const;

  private:
    sf::Vector2f mVelocity; // default ocnstructor initializes this vector to a zero vector
    virtual void updateCurrent(sf::Time deltaTime);

};

#include "entity.cpp"

#endif
