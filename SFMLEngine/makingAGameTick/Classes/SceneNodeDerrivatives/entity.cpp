#ifndef ENTITY_CPP
#define ENTITY_CPP

void Entity::SetVelocity(sf::Vector2f velocity)
{
  mVelocity = velocity;
}

void Entity::setVelocity(float velocityX, float velocityY)
{
  mVelocity.x = velocityX;
  mVelocity.y = velocityY;
}

sf::Vector2f Entity::getVelocity() const
{
  return mVelocity;
}

void Entity::updateCurrent(sf::Time deltaTime)
{
  move(mVelocity * deltaTime.asSeconds()); // shortcut for setPosition(getPosition() + offset)
}

#endif
