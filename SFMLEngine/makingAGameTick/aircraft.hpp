#ifndef AIRCRAFT_HPP
#define AIRCRAFT_HPP

#include "entity.hpp"

class Aircraft : public Entity
{
  public:
    enum Type
    {
      Eagle,
      Raptor
    };
  public:
    explicit Aircraft(Type type);

  private:
    Type mType;

};

#include "aircraft.cpp"
#endif
