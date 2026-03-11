# robotgo_demo

A simple demo of [go-vgo/robotgo](https://github.com/go-vgo/robotgo) — desktop
automation for Go (mouse, keyboard, screen, clipboard, window management).

## Requirements (Arch Linux, X11)

```bash
sudo pacman -S --needed gcc go libxtst libx11 libxkbcommon libxkbcommon-x11 \
    libpng xsel xclip libxcb
```

## Build & Run

```bash
cd robotgo_demo
go build -o robotgo_demo .
./robotgo_demo
```

**Note:** The program types text after a 2-second delay — focus a text editor
before running.

## What it does

1. Prints screen resolution
2. Reads and moves the mouse to screen center
3. Reads the pixel color at center
4. Writes/reads the clipboard
5. Types "Hello World!" into the focused window
6. Prints the active window title
