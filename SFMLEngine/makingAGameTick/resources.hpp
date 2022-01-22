#ifndef RESOURCES_HPP
#define RESOURCES_HPP

#include <assert.h>
// Mostly Chapter 2
// Handles resource management
namespace Textures // This gives us a scope for the enumerators which allows us to write Textures::Airplane instead of just Airplane to avoid name collisions in the global scope
{
  enum ID { Landscape, Airplane, Missile };
}

class TextureHolder
{
  public:
    void load(Textures::ID id, const std::string& filename);
    sf::Texture& get(Textures::ID id);
    const sf::Texture& get(Textures::ID id) const;
  private:
    std::map< Textures::ID, std::unique_ptr<sf::Texture> > mTextureMap;
    // unique_ptr are class templates that act like pointers, this allows us to work with heavyweight objects without copying them all the time, or we can store classes that are non-cpyable like sf::Shader
};



#include "resources.inl"

#endif // RESOURCES_HPP
