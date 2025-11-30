# Simple OpenGL FPS (C + FreeGLUT)

A tiny first-person demo using legacy OpenGL (compat) and FreeGLUT:

- Move with WASD, hold Tab or Q to sprint
- Aim with mouse (captured by default). Press M to toggle capture
- Shoot with Left Mouse or Space. Hit the red cube to score; it respawns
- Press Esc to quit

## Build

Requires development packages for OpenGL, GLU, FreeGLUT, and SDL2 (for audio).
On Debian/Ubuntu:

```sh
sudo apt-get update
sudo apt-get install -y build-essential freeglut3-dev libsdl2-dev pkg-config
```

Then build and run:

```sh
make -C C/fps
make -C C/fps run
```

If your distro uses different package names, install the equivalents of:

- libgl1, libglu1, freeglut (dev headers)

## Notes

- This uses old-school fixed-function OpenGL for simplicity and broad compatibility.
- Mouse is confined via glutWarpPointer; press M if you need to release it.
- SDL2 is used only for simple procedurally generated sound effects (shoot, hit, game over).
