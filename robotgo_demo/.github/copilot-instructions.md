# Copilot Instructions for robotgo_demo

## Overview

`robotgo_demo/` is a Go project using [go-vgo/robotgo](https://github.com/go-vgo/robotgo) for desktop automation on **Arch Linux, X11, i3 window manager**. Robotgo provides cross-platform control of mouse, keyboard, screen, clipboard, and window management.

## System Requirements (Arch Linux / X11)

All dependencies must be installed before building:

```bash
sudo pacman -S --needed gcc go libxtst libx11 libxkbcommon libxkbcommon-x11 \
    libpng xsel xclip libxcb
```

These provide:

- **GCC + Go** — compiler toolchain (robotgo uses cgo)
- **libxtst, libx11, libxcb** — X11 display and XTest extension
- **libxkbcommon, libxkbcommon-x11** — keyboard hook support (gohook)
- **libpng** — bitmap/screenshot capture
- **xsel, xclip** — clipboard read/write

## Build & Run

```bash
cd robotgo_demo
go build -o robotgo_demo .
./robotgo_demo
```

To update the dependency:

```bash
go get -u github.com/go-vgo/robotgo
go mod tidy
```

## Robotgo API Quick Reference

Use `import "github.com/go-vgo/robotgo"` in Go files. Key APIs:

### Mouse

```go
robotgo.Move(x, y)              // instant move
robotgo.MoveSmooth(x, y)        // human-like smooth move
robotgo.Click("left")           // click (left/right/center)
robotgo.DragSmooth(x, y)        // drag to position
robotgo.ScrollDir(n, "up")      // scroll direction
x, y := robotgo.Location()      // current mouse position
```

### Keyboard

```go
robotgo.Type("text")              // type a string
robotgo.KeyTap("enter")          // tap a single key
robotgo.KeyTap("a", "ctrl")      // key combo (ctrl+a)
robotgo.KeyToggle("shift")       // hold key down
robotgo.KeyToggle("shift", "up") // release key
```

### Screen

```go
sx, sy := robotgo.GetScreenSize()        // screen dimensions
color := robotgo.GetPixelColor(x, y)     // hex color at pixel
bit := robotgo.CaptureScreen(x, y, w, h) // capture region
defer robotgo.FreeBitmap(bit)            // always free bitmaps
img := robotgo.ToImage(bit)              // convert to Go image
```

### Clipboard

```go
robotgo.WriteAll("text")         // write to clipboard
text, err := robotgo.ReadAll()   // read from clipboard
```

### Window

```go
title := robotgo.GetTitle()               // active window title
pids, err := robotgo.FindIds("firefox")   // find PIDs by name
robotgo.ActivePid(pid)                    // focus window by PID
robotgo.ActiveName("firefox")             // focus window by name
```

### Event Hooks (via gohook)

```go
import hook "github.com/robotn/gohook"

hook.Register(hook.KeyDown, []string{"q", "ctrl"}, func(e hook.Event) {
    hook.End()
})
s := hook.Start()
<-hook.Process(s)
```

### Timing

```go
robotgo.Sleep(1)              // sleep 1 second
robotgo.MilliSleep(500)       // sleep 500ms
robotgo.MouseSleep = 300      // default delay between mouse ops
robotgo.KeySleep = 100        // default delay between key ops
```

## Key Docs & Links

- [Full API docs](https://github.com/go-vgo/robotgo/blob/master/docs/doc.md)
- [Key name reference](https://github.com/go-vgo/robotgo/blob/master/docs/keys.md)
- [Examples](https://github.com/go-vgo/robotgo/blob/master/examples)
- [GoDoc](https://pkg.go.dev/github.com/go-vgo/robotgo)

## Conventions

- Always `defer robotgo.FreeBitmap(bit)` after `CaptureScreen` to avoid memory leaks.
- Use `MoveSmooth` over `Move` when simulating human interaction.
- Add `time.Sleep` or `robotgo.MilliSleep` before typing to give the user time to focus the target window.
- Robotgo operates on X11 only — this project does **not** support Wayland.
- The compiled binary is git-ignored; always build from source.

## Gotchas

- **cgo required**: robotgo uses C bindings. `CGO_ENABLED=1` must be set (it's the default on native builds).
- **X11 only**: will not work under Wayland. Ensure `$DISPLAY` is set.
- **Root not needed**: runs as a regular user with X11 access.
- **Bitmap capture** may fail if no X display is available (e.g., headless/SSH without X forwarding).
- **`png.h: No such file or directory`**: install `libpng` (`sudo pacman -S libpng`).

## Project Structure

```
robotgo_demo/
├── .gitignore      # ignores compiled binary
├── go.mod          # Go module (robotgo_demo)
├── go.sum          # dependency checksums
├── main.go         # demo: mouse, keyboard, screen, clipboard, window
└── README.md       # user-facing docs
```
