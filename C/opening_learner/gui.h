#ifndef GUI_H
#define GUI_H

#include <SDL2/SDL.h>
#include <stdbool.h>

typedef struct
{
    SDL_Window   *window;
    SDL_Renderer *renderer;
    int           win_w, win_h;
    bool          flipped; // true if black at bottom
} Gui;

typedef struct
{
    int  from_sq; // 0..63 or -1
    int  to_sq;   // 0..63 or -1
    char promo;   // 'q','r','b','n' or 0
    bool clicked;
} GuiSelection;

bool gui_init(Gui *g, int w, int h, const char *title);
void gui_destroy(Gui *g);
void gui_set_flipped(Gui *g, bool flipped);
void gui_draw(Gui *g, const char board[64], const GuiSelection *sel, const char *status_line);
// Returns true if something changed. If a key was pressed, key_out receives SDL_Keycode else 0.
bool gui_poll_move(Gui *g, GuiSelection *sel, bool *quit_requested, int *key_out);
int  gui_coord_to_sq(Gui *g, int x, int y);

// colors
extern const SDL_Color COLOR_LIGHT;
extern const SDL_Color COLOR_DARK;
extern const SDL_Color COLOR_GRID;
extern const SDL_Color COLOR_SEL;
extern const SDL_Color COLOR_TEXT;

#endif
