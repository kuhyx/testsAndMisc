#ifndef WORLD_CPP // ZA WARUDO
#define WORLD_CPP

World::World(sf::RenderWindow& window)
: mWindow(window)
, mWorldView(window.getDefaultView())
, mWorldBounds
(
  WORLD_LEFT_X_POSITION,
  WORLD_TOP_Y_POSITION,
  mWorldView.getSize().x,
  WORLD_HEIGHT
)
, mSpawnPosition
(
  mWorldView.getSize().x / 2.f,
  mWorldBounds.height - mWorldView.getSize().y
)
, mScrollSpeed ( WORLD_SCROLL_SPEED )
, mPlayerAircraft(nullptr)
{
  // loadTextures();
  // buildScene();
  // mWorldView.setCenter(mSpawnPosition);
}

#endif // WORLD_CPP
