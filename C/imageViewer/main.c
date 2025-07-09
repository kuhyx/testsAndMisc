#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <SDL2/SDL.h>
#include <SDL2/SDL_image.h>

#define WINDOW_WIDTH 800
#define WINDOW_HEIGHT 600
#define MAX_PATH_LEN 512

typedef struct {
    SDL_Window* window;
    SDL_Renderer* renderer;
    SDL_Texture* texture;
    char current_file[MAX_PATH_LEN];
    int image_width;
    int image_height;
    float zoom_factor;
    int offset_x;
    int offset_y;
    int dragging;
    int last_mouse_x;
    int last_mouse_y;
} ImageViewer;

int init_viewer(ImageViewer* viewer) {
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL could not initialize! SDL_Error: %s\n", SDL_GetError());
        return 0;
    }

    int img_flags = IMG_INIT_JPG | IMG_INIT_PNG;
    if (!(IMG_Init(img_flags) & img_flags)) {
        printf("SDL_image could not initialize! SDL_image Error: %s\n", IMG_GetError());
        SDL_Quit();
        return 0;
    }

    viewer->window = SDL_CreateWindow("JPG Image Viewer",
                                      SDL_WINDOWPOS_UNDEFINED,
                                      SDL_WINDOWPOS_UNDEFINED,
                                      WINDOW_WIDTH,
                                      WINDOW_HEIGHT,
                                      SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    
    if (!viewer->window) {
        printf("Window could not be created! SDL_Error: %s\n", SDL_GetError());
        IMG_Quit();
        SDL_Quit();
        return 0;
    }

    viewer->renderer = SDL_CreateRenderer(viewer->window, -1, SDL_RENDERER_ACCELERATED);
    if (!viewer->renderer) {
        printf("Renderer could not be created! SDL_Error: %s\n", SDL_GetError());
        SDL_DestroyWindow(viewer->window);
        IMG_Quit();
        SDL_Quit();
        return 0;
    }

    viewer->texture = NULL;
    viewer->current_file[0] = '\0';
    viewer->zoom_factor = 1.0f;
    viewer->offset_x = 0;
    viewer->offset_y = 0;
    viewer->dragging = 0;
    viewer->image_width = 0;
    viewer->image_height = 0;

    return 1;
}

int load_image(ImageViewer* viewer, const char* filename) {
    if (viewer->texture) {
        SDL_DestroyTexture(viewer->texture);
        viewer->texture = NULL;
    }

    SDL_Surface* surface = IMG_Load(filename);
    if (!surface) {
        printf("Unable to load image %s! SDL_image Error: %s\n", filename, IMG_GetError());
        return 0;
    }

    viewer->texture = SDL_CreateTextureFromSurface(viewer->renderer, surface);
    if (!viewer->texture) {
        printf("Unable to create texture from %s! SDL_Error: %s\n", filename, SDL_GetError());
        SDL_FreeSurface(surface);
        return 0;
    }

    viewer->image_width = surface->w;
    viewer->image_height = surface->h;

    SDL_FreeSurface(surface);

    strncpy(viewer->current_file, filename, MAX_PATH_LEN - 1);
    viewer->current_file[MAX_PATH_LEN - 1] = '\0';

    viewer->zoom_factor = 1.0f;
    viewer->offset_x = 0;
    viewer->offset_y = 0;

    int window_w, window_h;
    SDL_GetWindowSize(viewer->window, &window_w, &window_h);
    
    float scale_x = (float)window_w / viewer->image_width;
    float scale_y = (float)window_h / viewer->image_height;
    float auto_scale = (scale_x < scale_y) ? scale_x : scale_y;
    
    if (auto_scale < 1.0f) {
        viewer->zoom_factor = auto_scale * 0.9f;
    }

    printf("Loaded image: %s (%dx%d)\n", filename, viewer->image_width, viewer->image_height);
    return 1;
}

void render_image(ImageViewer* viewer) {
    SDL_SetRenderDrawColor(viewer->renderer, 32, 32, 32, 255);
    SDL_RenderClear(viewer->renderer);

    if (!viewer->texture) {
        SDL_RenderPresent(viewer->renderer);
        return;
    }

    int scaled_width = (int)(viewer->image_width * viewer->zoom_factor);
    int scaled_height = (int)(viewer->image_height * viewer->zoom_factor);

    int window_w, window_h;
    SDL_GetWindowSize(viewer->window, &window_w, &window_h);

    int x = (window_w - scaled_width) / 2 + viewer->offset_x;
    int y = (window_h - scaled_height) / 2 + viewer->offset_y;

    SDL_Rect dest_rect = {x, y, scaled_width, scaled_height};
    SDL_RenderCopy(viewer->renderer, viewer->texture, NULL, &dest_rect);

    SDL_RenderPresent(viewer->renderer);
}

void handle_zoom(ImageViewer* viewer, float zoom_delta, int mouse_x, int mouse_y) {
    float old_zoom = viewer->zoom_factor;
    viewer->zoom_factor += zoom_delta;
    
    if (viewer->zoom_factor < 0.1f) viewer->zoom_factor = 0.1f;
    if (viewer->zoom_factor > 10.0f) viewer->zoom_factor = 10.0f;

    float zoom_ratio = viewer->zoom_factor / old_zoom;
    
    int window_w, window_h;
    SDL_GetWindowSize(viewer->window, &window_w, &window_h);
    
    int center_x = window_w / 2;
    int center_y = window_h / 2;
    
    viewer->offset_x = (viewer->offset_x - (mouse_x - center_x)) * zoom_ratio + (mouse_x - center_x);
    viewer->offset_y = (viewer->offset_y - (mouse_y - center_y)) * zoom_ratio + (mouse_y - center_y);
}

void print_help() {
    printf("\n=== JPG Image Viewer Controls ===\n");
    printf("Mouse wheel / +/-: Zoom in/out\n");
    printf("Mouse drag: Pan image\n");
    printf("R: Reset zoom and position\n");
    printf("F: Fit image to window\n");
    printf("H: Show this help\n");
    printf("ESC/Q: Quit\n");
    printf("==================================\n\n");
}

void cleanup_viewer(ImageViewer* viewer) {
    if (viewer->texture) {
        SDL_DestroyTexture(viewer->texture);
    }
    if (viewer->renderer) {
        SDL_DestroyRenderer(viewer->renderer);
    }
    if (viewer->window) {
        SDL_DestroyWindow(viewer->window);
    }
    IMG_Quit();
    SDL_Quit();
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        printf("Usage: %s <image_file.jpg>\n", argv[0]);
        printf("Supported formats: JPG, JPEG, PNG, BMP, GIF, TIF\n");
        return 1;
    }

    ImageViewer viewer;
    
    if (!init_viewer(&viewer)) {
        printf("Failed to initialize image viewer!\n");
        return 1;
    }

    if (!load_image(&viewer, argv[1])) {
        printf("Failed to load image: %s\n", argv[1]);
        cleanup_viewer(&viewer);
        return 1;
    }

    print_help();

    int quit = 0;
    SDL_Event e;

    while (!quit) {
        while (SDL_PollEvent(&e)) {
            switch (e.type) {
                case SDL_QUIT:
                    quit = 1;
                    break;

                case SDL_KEYDOWN:
                    switch (e.key.keysym.sym) {
                        case SDLK_ESCAPE:
                        case SDLK_q:
                            quit = 1;
                            break;

                        case SDLK_r:
                            viewer.zoom_factor = 1.0f;
                            viewer.offset_x = 0;
                            viewer.offset_y = 0;
                            printf("Reset view\n");
                            break;

                        case SDLK_f:
                            {
                                int window_w, window_h;
                                SDL_GetWindowSize(viewer.window, &window_w, &window_h);
                                
                                float scale_x = (float)window_w / viewer.image_width;
                                float scale_y = (float)window_h / viewer.image_height;
                                viewer.zoom_factor = ((scale_x < scale_y) ? scale_x : scale_y) * 0.9f;
                                viewer.offset_x = 0;
                                viewer.offset_y = 0;
                                printf("Fit to window (zoom: %.2f)\n", viewer.zoom_factor);
                            }
                            break;

                        case SDLK_PLUS:
                        case SDLK_EQUALS:
                            handle_zoom(&viewer, 0.1f, WINDOW_WIDTH/2, WINDOW_HEIGHT/2);
                            printf("Zoom: %.2f\n", viewer.zoom_factor);
                            break;

                        case SDLK_MINUS:
                            handle_zoom(&viewer, -0.1f, WINDOW_WIDTH/2, WINDOW_HEIGHT/2);
                            printf("Zoom: %.2f\n", viewer.zoom_factor);
                            break;

                        case SDLK_h:
                            print_help();
                            break;
                    }
                    break;

                case SDL_MOUSEWHEEL:
                    {
                        int mouse_x, mouse_y;
                        SDL_GetMouseState(&mouse_x, &mouse_y);
                        float zoom_delta = e.wheel.y * 0.1f;
                        handle_zoom(&viewer, zoom_delta, mouse_x, mouse_y);
                        printf("Zoom: %.2f\n", viewer.zoom_factor);
                    }
                    break;

                case SDL_MOUSEBUTTONDOWN:
                    if (e.button.button == SDL_BUTTON_LEFT) {
                        viewer.dragging = 1;
                        viewer.last_mouse_x = e.button.x;
                        viewer.last_mouse_y = e.button.y;
                    }
                    break;

                case SDL_MOUSEBUTTONUP:
                    if (e.button.button == SDL_BUTTON_LEFT) {
                        viewer.dragging = 0;
                    }
                    break;

                case SDL_MOUSEMOTION:
                    if (viewer.dragging) {
                        int dx = e.motion.x - viewer.last_mouse_x;
                        int dy = e.motion.y - viewer.last_mouse_y;
                        
                        viewer.offset_x += dx;
                        viewer.offset_y += dy;
                        
                        viewer.last_mouse_x = e.motion.x;
                        viewer.last_mouse_y = e.motion.y;
                    }
                    break;

                case SDL_WINDOWEVENT:
                    if (e.window.event == SDL_WINDOWEVENT_RESIZED) {
                        printf("Window resized to %dx%d\n", e.window.data1, e.window.data2);
                    }
                    break;
            }
        }

        render_image(&viewer);
        SDL_Delay(16);
    }

    cleanup_viewer(&viewer);
    printf("Image viewer closed.\n");
    return 0;
}