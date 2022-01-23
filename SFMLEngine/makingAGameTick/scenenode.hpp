#ifndef SCENE_NODE_HPP
#define SCENE_NODE_HPP

class SceneNode : public sf::Transformable, public sf::Drawable, private sf::NonCopyable
// we derrive from transformable - to be able to store and modify position, rotation and scale
// we derrive from drawable - to be able to draw it on screen
// we derrive from noncopyable - so that copy constructor and copy assignemnt operators are disabled
// This is used to create scene graph (tree data structure) in order to manage transform hierarchies
{
  public:
    typedef std::unique_ptr<SceneNode> ScenePointer; // element types must be complete types and we do not want to manage memory ourselves so we use std::unique_ptr
  public:
    SceneNode();
    void attachChild(ScenePointer child);
    ScenePointer detachChild(const SceneNode& node);
  private:
    virtual void draw(sf::RenderTarget& target, sf::RenderStates states) const; // we override draw() function of sf::Drawable
    // Virtual functions are member functions whose behavior can be overridden in derived classes
    // draw() function allows our class to be used like this:
    /*
    sf::RenderWindow window(...);
    SceneNode::ScenePointer node(...);
    window.draw(*node);
    */
    virtual void drawCurrent(sf::RenderTarget& target, sf::RenderStates states) const; // draws only the current object, and not the children
  private:
    std::vector<ScenePointer> mChildren;
    SceneNode* mParent;

};

#include "scenenode.cpp"

#endif
