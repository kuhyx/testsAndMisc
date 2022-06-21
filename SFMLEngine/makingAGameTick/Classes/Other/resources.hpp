#ifndef RESOURCES_HPP
#define RESOURCES_HPP

#include <assert.h>
// Mostly Chapter 2
// Handles resource management




namespace Textures // This gives us a scope for the enumerators which allows us to write Textures::Airplane instead of just Airplane to avoid name collisions in the global scope
{
  enum ID
  {
    Eagle,
    Raptor,
    Desert
  };
}

template <typename Resource, typename Identifier>
class ResourceHolder
{
  public:
    void load(Identifier id, const std::string& filename);
    Resource& get(Identifier id);
    const Resource& get(Identifier id) const;
    template <typename Parameter>
    void load(Identifier id, const std::string& filename, const Parameter& secondParameter);
    // Second parameter can be of sf::Shader::Type or std::string&
  private:
    std::map< Identifier, std::unique_ptr<Resource> > mResourceMap;
    // unique_ptr are class templates that act like pointers, this allows us to work with heavyweight objects without copying them all the time, or we can store classes that are non-cpyable like sf::Shader
};

typedef ResourceHolder<sf::Texture, Textures::ID> TextureHolder;



#include "resources.inl"

#endif // RESOURCES_HPP
