#ifndef RESOURCES_INL
#define RESOURCES_INL

template <typename Resource, typename Identifier>
void ResourceHolder<Resource, Identifier>::load(Identifier id, const std::string& filename)
// Function to load a resource, it takes one parameter for filename and one for identifier
{
  std::unique_ptr<Resource> texture(new Resource()); // Create sf:Texture and store it in the unique pointer
  if(!texture -> loadFromFile(filename))// Load the texture from the filename
  {
    throw std::runtime_error(TEXTURE_LOAD_ERROR + filename);
  }
  auto inserted = mResourceMap.insert(std::make_pair(id, std::move(texture))); // Insert texture into map mResourceMap, std::move used to take ownership from texture variable and transfer it to std::make_pair(), std::move moves the resource into a new place and removes it from earlier place https://en.cppreference.com/w/cpp/utility/move
  assert(inserted.second);
}

template <typename Resource, typename Identifier>
Resource& ResourceHolder<Resource, Identifier>::get(Identifier id) // returns a reference to a texture
{
  auto found = mResourceMap.find(id); // find returns an iterator to the found element or end() if nothing was found
  assert(found != mResourceMap.end());
  return *found -> second; // We have to access the second member of the pointer, then we deference it and get a texture
}

template <typename Resource, typename Identifier>
const Resource& ResourceHolder<Resource, Identifier>::get(Identifier id) const // we need to be able to invoke get() also if we only have a pointer/reference to the const ResourceHolder<Resource, Identifier>, it returns const Resource so the texture cannot be changed by caller
{
  auto found = mResourceMap.find(id); // find returns an iterator to the found element or end() if nothing was found
  return *found -> second; // We have to access the second member of the pointer, then we deference it and get a texture
}

#endif // RESOURCES_INL
