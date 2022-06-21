#ifndef WORLD_HPP // ZA WARUDO
#define WORLD_HPP

#include <array>
#include "../SceneNodeDerrivatives/SceneNode.hpp"
#include "../SceneNodeDerrivatives/aircraft.hpp"

class World : private sf::NonCopyable // We only have one world  and we do not want to copy it #StopClimateChange amiright
{
  public:
    explicit World(sf::RenderWindow& window);
    void update(sf::Time deltaTime);
    void draw();
  private:
    void loadTextures();
    void buildScene();

  private:
    enum Layer
    {
      Background,
      Air,
      LayerCount
    };

  private:
    sf::RenderWindow& mWindow; // reference to the render window
    sf::View mWorldView; // current world's view
    TextureHolder mTextures; // All the textures needed inside the world
    SceneNode mSceneGraph;
    std::array<SceneNode*, LayerCount> mSceneLayers; // Pointers to access the scene graph's layerr nodes

    sf::FloatRect mWorldBounds; // Bounding rectangle of the world
    sf::Vector2f mSpawnPosition; // Where player plane appears in the beginning
    float mScrollSpeed; // Speed with which the world is scrolled
    Aircraft* mPlayerAircraft; // Pointer to player aircraft
};

// std::array is a class template for fixed size static arrays, same functionality, performance as C arrays but allows copies, assignment, passing or returning objects from the function, additional safety and usefull methods like size(), begin() or end()

#include "world.cpp"
#endif // WORLD_HPP
