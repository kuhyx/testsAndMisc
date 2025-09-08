#include "gui.h"
#include <SDL2/SDL.h>
#include <stdio.h>

const SDL_Color COLOR_LIGHT = { 238, 238, 210, 255 }; // light square (not pure white)
const SDL_Color COLOR_DARK  = { 118, 150, 86, 255 };  // dark square (not pure black)
const SDL_Color COLOR_GRID  = { 20, 20, 20, 255 };    // thick outline
const SDL_Color COLOR_SEL   = { 200, 50, 50, 200 };   // selection highlight
const SDL_Color COLOR_TEXT  = { 10, 10, 10, 255 };

static void set_color(SDL_Renderer *r, SDL_Color c) {
    SDL_SetRenderDrawColor(r, c.r, c.g, c.b, c.a);
}

bool gui_init(Gui *g, int w, int h, const char *title) {
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init error: %s\n", SDL_GetError());
        return false;
    }
    g->window = SDL_CreateWindow(title, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, w, h, SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    if (!g->window) {
        fprintf(stderr, "SDL_CreateWindow error: %s\n", SDL_GetError());
        return false;
    }
    g->renderer = SDL_CreateRenderer(g->window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!g->renderer) {
        fprintf(stderr, "SDL_CreateRenderer error: %s\n", SDL_GetError());
        return false;
    }
    g->win_w = w; g->win_h = h; g->flipped = false;
    return true;
}

void gui_destroy(Gui *g) {
    if (g->renderer) SDL_DestroyRenderer(g->renderer);
    if (g->window) SDL_DestroyWindow(g->window);
    SDL_Quit();
}

void gui_set_flipped(Gui *g, bool flipped) { g->flipped = flipped; }

static void draw_rect(SDL_Renderer *r, int x, int y, int w, int h, SDL_Color c) {
    set_color(r, c);
    SDL_Rect rc = { x, y, w, h };
    SDL_RenderFillRect(r, &rc);
}

static void draw_outline(SDL_Renderer *r, int x, int y, int w, int h, int thickness, SDL_Color c) {
    set_color(r, c);
    for (int i=0;i<thickness;i++) {
        SDL_Rect rc = { x+i, y+i, w-2*i, h-2*i };
        SDL_RenderDrawRect(r, &rc);
    }
}

static void draw_piece_letter(SDL_Renderer *r, int x, int y, int size, char p) {
    // Minimal: draw a filled circle/square plus an initial letter approximated with rectangles.
    // To keep dependencies minimal, no TTF. Ensure contrast: white pieces light, black pieces dark.
    SDL_Color fill = (p >= 'A' && p <= 'Z') ? (SDL_Color){250, 250, 250, 255} : (SDL_Color){30, 30, 30, 255};
    SDL_Color glyph = (p >= 'A' && p <= 'Z') ? (SDL_Color){30, 30, 30, 255} : (SDL_Color){240, 240, 240, 255};
    // Base disk
    draw_rect(r, x+size*0.15, y+size*0.15, (int)(size*0.7), (int)(size*0.7), fill);
    // Glyph: draw a simple letter-like mark
    set_color(r, glyph);
    // vertical bar
    SDL_Rect bar1 = { x + size/2 - size/16, y + size/3, size/8, size/3 };
    SDL_RenderFillRect(r, &bar1);
    // top bar
    SDL_Rect bar2 = { x + size/3, y + size/3 - size/10, size/3, size/10 };
    SDL_RenderFillRect(r, &bar2);
}

void gui_draw(Gui *g, const char board[64], const GuiSelection *sel, const char *status_line) {
    SDL_GetWindowSize(g->window, &g->win_w, &g->win_h);

    set_color(g->renderer, (SDL_Color){ 35, 35, 35, 255 });
    SDL_RenderClear(g->renderer);

    int size = (g->win_w < g->win_h ? g->win_w : g->win_h) - 40; // margins
    if (size < 200) size = 200;
    int cell = size / 8;
    size = cell * 8;
    int ox = (g->win_w - size)/2;
    int oy = (g->win_h - size)/2;

    // Board outline (thick)
    draw_outline(g->renderer, ox-6, oy-6, size+12, size+12, 6, COLOR_GRID);

    // Squares
    for (int r=0;r<8;r++) {
        for (int f=0;f<8;f++) {
            int idx = g->flipped ? (63 - (r*8+f)) : (r*8+f);
            SDL_Color c = ((r+f)&1) ? COLOR_DARK : COLOR_LIGHT;
            draw_rect(g->renderer, ox + f*cell, oy + r*cell, cell, cell, c);

            char p = board[idx];
            if (p != '.' && p != '\0') {
                draw_piece_letter(g->renderer, ox + f*cell, oy + r*cell, cell, p);
            }
        }
    }

    // Selection overlay
    if (sel && sel->clicked && sel->from_sq >= 0) {
        int s = sel->from_sq;
        int rr = g->flipped ? 7 - (s/8) : (s/8);
        int ff = g->flipped ? 7 - (s%8) : (s%8);
        draw_outline(g->renderer, ox + ff*cell+2, oy + rr*cell+2, cell-4, cell-4, 3, COLOR_SEL);
    }

    // Status strip
    draw_outline(g->renderer, 10, g->win_h - 40, g->win_w - 20, 30, 2, COLOR_GRID);
    // Without TTF, we can't render text; draw a minimal indicator bar to signal state.
    // If status_line indicates success/failure, alter color.
    SDL_Color bar = { 80, 120, 200, 255 };
    if (status_line && status_line[0]) {
        if (SDL_strstr(status_line, "Correct")) bar = (SDL_Color){80, 200, 120, 255};
        else if (SDL_strstr(status_line, "Wrong")) bar = (SDL_Color){200, 80, 80, 255};
    }
    draw_rect(g->renderer, 12, g->win_h - 38, g->win_w - 24, 26, bar);

    SDL_RenderPresent(g->renderer);
}

int gui_coord_to_sq(Gui *g, int x, int y) {
    int w, h; SDL_GetWindowSize(g->window, &w, &h);
    int size = (w < h ? w : h) - 40; if (size < 200) size = 200;
    int cell = size / 8; size = cell * 8;
    int ox = (w - size)/2; int oy = (h - size)/2;
    if (x < ox || y < oy || x >= ox+size || y >= oy+size) return -1;
    int f = (x - ox) / cell;
    int r = (y - oy) / cell;
    int sq = r*8 + f;
    if (g->flipped) sq = 63 - sq;
    return sq;
}

bool gui_poll_move(Gui *g, GuiSelection *sel, bool *quit_requested, int *key_out) {
    SDL_Event e;
    bool updated = false;
    if (key_out) *key_out = 0;
    while (SDL_PollEvent(&e)) {
        if (e.type == SDL_QUIT) { if (quit_requested) *quit_requested = true; }
        else if (e.type == SDL_WINDOWEVENT && e.window.event == SDL_WINDOWEVENT_SIZE_CHANGED) {
            updated = true;
        } else if (e.type == SDL_MOUSEBUTTONDOWN && e.button.button == SDL_BUTTON_LEFT) {
            int sq = gui_coord_to_sq(g, e.button.x, e.button.y);
            if (sq >= 0) {
                if (!sel->clicked) { sel->from_sq = sq; sel->to_sq = -1; sel->clicked = true; }
                else { sel->to_sq = sq; updated = true; }
            }
        } else if (e.type == SDL_KEYDOWN) {
            if (e.key.keysym.sym == SDLK_ESCAPE) { sel->clicked = false; sel->from_sq = sel->to_sq = -1; updated = true; }
            if (key_out) *key_out = e.key.keysym.sym;
        }
    }
    return updated;
}
