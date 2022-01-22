#ifndef RESOURCES_INL
#define RESOURCES_INL

template <typename Resource, typename Identifier>
void ResourceHolder<Resource, Identifier>::load(Identifier id, const std::string& filename)
// Function to load a resource, it takes one parameter for filename and one for identifier
{
  std::unique_ptr<Resource> resource(new Resource()); // Create sf:Texture and store it in the unique pointer
  if(!resource -> loadFromFile(filename))// Load the resource from the filename
  {
    throw std::runtime_error(TEXTURE_LOAD_ERROR + filename);
  }
  auto inserted = mResourceMap.insert(std::make_pair(id, std::move(resource))); // Insert resource into map mResourceMap, std::move used to take ownership from resource variable and transfer it to std::make_pair(), std::move moves the resource into a new place and removes it from earlier place https://en.cppreference.com/w/cpp/utility/move
  assert(inserted.second);
}

template <typename Resource, typename Identifier>
Resource& ResourceHolder<Resource, Identifier>::get(Identifier id) // returns a reference to a resource
{
  auto found = mResourceMap.find(id); // find returns an iterator to the found element or end() if nothing was found
  assert(found != mResourceMap.end());
  return *found -> second; // We have to access the second member of the pointer, then we deference it and get a resource
}

template <typename Resource, typename Identifier>
const Resource& ResourceHolder<Resource, Identifier>::get(Identifier id) const // we need to be able to invoke get() also if we only have a pointer/reference to the const ResourceHolder<Resource, Identifier>, it returns const Resource so the resource cannot be changed by caller
{
  auto found = mResourceMap.find(id); // find returns an iterator to the found element or end() if nothing was found
  assert(found != mResourceMap.end());
  return *found -> second; // We have to access the second member of the pointer, then we deference it and get a resource
}

template <typename Resource, typename Identifier>
template <typename Parameter>
void ResourceHolder<Resource, Identifier>::load(Identifier id, const std::string& filename, const Parameter& secondParameter) // loads Shaders
{
  std::unique_ptr<Resource> resource(new Resource()); // Create sf:Texture and store it in the unique pointer
  if(!resource -> loadFromFile(filename, secondParameter))// Load the resource from the filename
  {
    throw std::runtime_error(TEXTURE_LOAD_ERROR + filename);
  }
  auto inserted = mResourceMap.insert(std::make_pair(id, std::move(resource))); // Insert resource into map mResourceMap, std::move used to take ownership from resource variable and transfer it to std::make_pair(), std::move moves the resource into a new place and removes it from earlier place https://en.cppreference.com/w/cpp/utility/move
  assert(inserted.second);
}

#endif // RESOURCES_INL
