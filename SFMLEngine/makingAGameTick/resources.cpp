#ifndef RESOURCES_CPP
#define RESOURCES_CPP

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

void TextureHolder::load(Textures::ID id, const std::string& filename)
// Function to load a resource, it takes one parameter for filename and one for identifier
{
  std::unique_ptr<sf::Texture> texture(new sf::Texture()); // Create sf:Texture and store it in the unique pointer
  if(!texture -> loadFromFile(filename))// Load the texture from the filename
  {
    throw std::runtime_error(TEXTURE_LOAD_ERROR + filename);
  }
  auto inserted = mTextureMap.insert(std::make_pair(id, std::move(texture))); // Insert texture into map mTextureMap, std::move used to take ownership from texture variable and transfer it to std::make_pair(), std::move moves the resource into a new place and removes it from earlier place https://en.cppreference.com/w/cpp/utility/move
  assert(inserted.second);
}

sf::Texture& TextureHolder::get(Textures::ID id) // returns a reference to a texture
{
  auto found = mTextureMap.find(id); // find returns an iterator to the found element or end() if nothing was found
  assert(found != mTextureMap.end());
  return *found -> second; // We have to access the second member of the pointer, then we deference it and get a texture
}

const sf::Texture& TextureHolder::get(Textures::ID id) const // we need to be able to invoke get() also if we only have a pointer/reference to the const TextureHolder, it returns const sf::Texture so the texture cannot be changed by caller
{
  auto found = mTextureMap.find(id); // find returns an iterator to the found element or end() if nothing was found
  return *found -> second; // We have to access the second member of the pointer, then we deference it and get a texture
}

#endif //RESOUIRCES_CPP
