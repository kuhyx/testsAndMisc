#ifndef WORLD_CPP // ZA WARUDO
#define WORLD_CPP

#include <cstddef> // std::size_t
#include "../SceneNodeDerrivatives/SpriteNode.hpp"

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
  loadTextures();
  buildScene();
  mWorldView.setCenter(mSpawnPosition);
}

void World::loadTextures()
{
  mTextures.load(Textures::Eagle, PATH_TO_EAGLE_TEXTURE);
  mTextures.load(Textures::Raptor, PATH_TO_RAPTOR_TEXTURE);
  mTextures.load(Textures::Desert, PATH_TO_DESERT_TEXTURE);
}

void World::buildScene()
{
  for (std::size_t i = 0; i < LayerCount; i++) // initialization of scene layers, iterate through array of layer node pointers
  {
    SceneNode::ScenePointer layer(new SceneNode());
    mSceneLayers[i] = layer.get(); // initialize elments of this arry

    mSceneGraph.attachChild(std::move(layer)); // attach new node to the scene graph's root node
  }

  sf::Texture& texture = mTextures.get(Textures::Desert);
  sf::IntRect textureRect(mWorldBounds);
  texture.setRepeated(true); // make desert texture repeat itself

  std::unique_ptr<SpriteNode> backgroundSprite(new SpriteNode(texture, textureRect)); // SpriteNode class that links to the desrt texture, our sprite will be as big as the whole world because we passed the texture rectangle
  backgroundSprite -> setPosition(mWorldBounds.left, mWorldBounds.top);
  mSceneLayers[Background] -> attachChild(std::move(backgroundSprite));

  // Adding airplanes
  std::unique_ptr<Aircraft> leader(new Aircraft(Aircraft::Eagle, mTextures)); // we create the player's airplane
  mPlayerAircraft = leader.get();
  mPlayerAircraft -> setPosition(mSpawnPosition); // Set player position
  mPlayerAircraft -> setVelocity(PLAYER_SIDEWARD_VELOCITY, mScrollSpeed); // forward velocity equals scroll speed, sideward velocity equals PLAYER_SIDEWARD_VELOCITY
  mSceneLayers[Air] -> attachChild(std::move(leader)); // we attach the plane to the Air scene layer

  std::unique_ptr<Aircraft> leftEscort(new Aircraft(Aircraft::Raptor, mTextures)); // create new airplane
  leftEscort -> setPosition(LEFT_ESCORT_X_POSITION, LEFT_ESCORT_Y_POSITION); // Set new airplane position
  mPlayerAircraft -> attachChild(std::move(leftEscort)); // leftEscort is now a child of player aircraft and it will folow it!

  std::unique_ptr<Aircraft> rightEscort(new Aircraft(Aircraft::Raptor, mTextures)); // create new airplane
  rightEscort -> setPosition(RIGHT_ESCORT_X_POSITION, RIGHT_ESCORT_Y_POSITION); // Set new airplane position
  mPlayerAircraft -> attachChild(std::move(rightEscort)); // leftEscort is now a child of player aircraft and it will folow it!


  }
#endif // WORLD_CPP
