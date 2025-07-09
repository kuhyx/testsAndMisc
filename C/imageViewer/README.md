# JPG Image Viewer

A simple, lightweight image viewer written in C using SDL2. Supports JPG, PNG, BMP, GIF, and TIF formats with zooming, panning, and basic image navigation features.

## Features

- **Multi-format support**: JPG, JPEG, PNG, BMP, GIF, TIF
- **Zoom functionality**: Mouse wheel or keyboard controls
- **Pan support**: Click and drag to move around zoomed images
- **Auto-fit**: Automatically fits large images to window
- **Responsive**: Resizable window with real-time updates
- **Keyboard shortcuts**: Quick controls for common operations

## Dependencies

The image viewer requires SDL2 and SDL2_image libraries.

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install libsdl2-dev libsdl2-image-dev
```

### Fedora/RHEL/CentOS
```bash
sudo dnf install SDL2-devel SDL2_image-devel
```

### Arch Linux
```bash
sudo pacman -S sdl2 sdl2_image
```

### macOS (with Homebrew)
```bash
brew install sdl2 sdl2_image
```

## Building

1. Install dependencies (see above)
2. Build the project:
```bash
make
```

Or use the dependency helper:
```bash
make deps-debian  # For Ubuntu/Debian
make deps-fedora  # For Fedora/RHEL/CentOS  
make deps-arch    # For Arch Linux
make
```

## Usage

```bash
./imageviewer <image_file>
```

Example:
```bash
./imageviewer photo.jpg
./imageviewer ../misc/randomJPG/14k/bloated_image_1.jpg
```

## Controls

| Control | Action |
|---------|--------|
| **Mouse wheel** | Zoom in/out |
| **+ / -** | Zoom in/out (keyboard) |
| **Mouse drag** | Pan around the image |
| **R** | Reset zoom and position to default |
| **F** | Fit image to window |
| **H** | Show help in console |
| **ESC / Q** | Quit the application |

## Features in Detail

### Zooming
- Use mouse wheel to zoom in/out at the mouse cursor position
- Keyboard shortcuts: `+` to zoom in, `-` to zoom out
- Zoom range: 0.1x to 10x
- Smart zoom behavior focuses on mouse position

### Panning
- Click and drag with left mouse button to move around zoomed images
- Smooth panning for precise positioning
- Works at any zoom level

### Auto-fit
- Large images are automatically scaled to fit the window when first loaded
- Press `F` to manually fit the current image to window
- Maintains aspect ratio

### Window Management
- Resizable window that adapts to content
- Real-time rendering updates
- Dark background for better image contrast

## Technical Details

- **Language**: C (C99 standard)
- **Graphics**: SDL2 for window management and rendering
- **Image loading**: SDL2_image for multi-format support
- **Performance**: Hardware-accelerated rendering when available
- **Memory**: Efficient texture management with proper cleanup

## Makefile Targets

- `make` or `make all` - Build the image viewer
- `make clean` - Remove built files
- `make test` - Run with a test image (if available in randomJPG folder)
- `make deps-debian` - Install dependencies on Ubuntu/Debian
- `make deps-fedora` - Install dependencies on Fedora/RHEL/CentOS
- `make deps-arch` - Install dependencies on Arch Linux
- `make help` - Show available targets and usage

## Troubleshooting

### "SDL could not initialize" Error
Make sure SDL2 development libraries are installed:
```bash
# Ubuntu/Debian
sudo apt-get install libsdl2-dev libsdl2-image-dev

# Check if libraries are found
pkg-config --libs sdl2
```

### "Unable to load image" Error
- Check that the image file exists and is readable
- Verify the image format is supported (JPG, PNG, BMP, GIF, TIF)
- Try with a different image file to isolate the issue

### Compilation Errors
- Ensure you have a C compiler installed (gcc or clang)
- Check that SDL2 headers are available
- Try rebuilding with `make clean && make`

## License

This project is open source. See the LICENSE file for details.

## Contributing

Feel free to submit issues and enhancement requests. The code is designed to be simple and educational while being fully functional.
