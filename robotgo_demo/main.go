// Package main demonstrates basic robotgo capabilities:
// mouse control, keyboard typing, screen info, and clipboard.
package main

import (
	"fmt"
	"time"

	"github.com/go-vgo/robotgo"
)

func main() {
	// --- Screen info ---
	sx, sy := robotgo.GetScreenSize()
	fmt.Printf("Screen size: %d x %d\n", sx, sy)

	// --- Mouse: read position, move, click ---
	x, y := robotgo.Location()
	fmt.Printf("Current mouse position: (%d, %d)\n", x, y)

	targetX, targetY := sx/2, sy/2
	fmt.Printf("Moving mouse to center (%d, %d)...\n", targetX, targetY)
	robotgo.MoveSmooth(targetX, targetY)
	time.Sleep(500 * time.Millisecond)

	nx, ny := robotgo.Location()
	fmt.Printf("Mouse is now at: (%d, %d)\n", nx, ny)

	// --- Pixel color at center ---
	color := robotgo.GetPixelColor(targetX, targetY)
	fmt.Printf("Pixel color at center: #%s\n", color)

	// --- Clipboard ---
	robotgo.WriteAll("Hello from robotgo!")
	text, err := robotgo.ReadAll()
	if err != nil {
		fmt.Println("Clipboard read error:", err)
	} else {
		fmt.Printf("Clipboard contents: %q\n", text)
	}

	// --- Keyboard: type into the currently focused window ---
	fmt.Println("Typing 'Hello World!' in 2 seconds (focus a text editor)...")
	time.Sleep(2 * time.Second)
	robotgo.Type("Hello World!")

	// --- Window: get active window title ---
	title := robotgo.GetTitle()
	fmt.Printf("Active window title: %q\n", title)

	fmt.Println("Done!")
}
