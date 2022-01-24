#ifndef AIRCRAFT_CPP
#define AIRCRAFT_CPP

Textures::ID toTextureID(Aircraft::Type type)
{
	switch (type)
	{
		case Aircraft::Eagle:
			return Textures::Eagle;

		case Aircraft::Raptor:
			return Textures::Raptor;

    default:
      return Textures::Eagle;
	}
	return Textures::Eagle;
}


Aircraft::Aircraft(Type type, const TextureHolder& textures) : mType(type), mSprite(textures.get(toTextureID(type)))
{
  sf::FloatRect bounds = mSprite.getLocalBounds(); // we get local bounding rectangle which means that we do not take transforms into account, as opposed to getGlobalBounds()
  mSprite.setOrigin(bounds.width / 2.f, bounds.height / 2.f); // we want to set origin of the sprite to the middle of a rectangle around it
}

void Aircraft::drawCurrent(sf::RenderTarget& target, sf::RenderStates states) const
{
  target.draw(mSprite, states);
}

#endif
