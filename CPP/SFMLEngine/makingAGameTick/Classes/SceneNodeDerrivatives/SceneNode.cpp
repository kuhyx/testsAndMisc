#ifndef SCENE_NODE_CPP
#define SCENE_NODE_CPP


void SceneNode::attachChild(ScenePointer child) // takes ownership of the scene node
{
  child -> mParent = this;
  mChildren.push_back(std::move(child));
}

SceneNode::ScenePointer SceneNode::detachChild(const SceneNode& node) // finds node, releases it and returns it to caller
{
  auto found = std::find_if
  (
    mChildren.begin(), mChildren.end(),
    [&] (ScenePointer& p) -> bool { return p.get() == &node; }
  );
  // This is lambda expression
  // [&] (ScenePointer& p) -> bool { return p.get() == &node; }
  // [&] - how many and in what way will the lambda expression have access to the variables in surrounding scope, [] - no variables [&] - all variables by reference [=] - all variables by value
  // (ScenePointer& p) - parameters passed to the function
  // -> bool - return type
  //  function body encolsed in {}
  assert(found != mChildren.end()); // We check validity of the iterator of the found element

  ScenePointer result = std::move(*found); // we move the found node out of the container to result
  result -> mParent = nullptr; // node's parent is set to null pointer
  mChildren.erase(found); // we erase this element from the container
  return result; // and we return the pointer to the node
}

void SceneNode::drawCurrent(sf::RenderTarget& target, sf::RenderStates states) const
{

}

void SceneNode::draw(sf::RenderTarget& target, sf::RenderStates states) const
{
  states.transform *= getTransform();
  // *= combines the parent's absolute transform with the relative one of the current node;
  // states.transform contains the absolute world transform
  drawCurrent(target, states); // now we can draw the derived object using states, this is similar to how sf::Sprite handles transforms

  for (const ScenePointer& child : mChildren)
  {
    child -> draw(target, states); // we also need to draw all the child nodes
  }
}

void SceneNode::updateCurrent(sf::Time deltaTime)
{

}

void SceneNode::updateChildren(sf::Time deltaTime)
{
  for (const ScenePointer& child : mChildren)
  {
    child -> update(deltaTime); // we also need to draw all the child nodes
  }
}

void SceneNode::update(sf::Time deltaTime)
{
  updateCurrent(deltaTime);
  updateChildren(deltaTime);
}

sf::Transform SceneNode::getWorldTransform() const
{
  sf::Transform transform = sf::Transform::Identity; // sf::Transform::Identity represents the identity transform - it does not have any effecft on the object, it is not necessary in the code but it clarifies how transforms are applied
  for (const SceneNode* node = this; node != nullptr; node = node -> mParent)
  {
    transform = node -> getTransform() * transform;
  }
  return transform;
}

sf::Vector2f SceneNode::getWorldPosition() const
{
  return getWorldTransform() * sf::Vector2f();
}



#endif
