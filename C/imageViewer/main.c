#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#include <strings.h>
#include <SDL2/SDL.h>
#include <SDL2/SDL_image.h>

#define WINDOW_WIDTH 800
#define WINDOW_HEIGHT 600
#define MAX_PATH_LEN 512
#define MAX_FILES 1000

typedef struct {
    char** files;
    int count;
    int current_index;
    char base_dir[MAX_PATH_LEN];
} FileList;

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
    FileList file_list;
    
    // Auto-navigation state
    int left_key_held;
    int right_key_held;
    Uint32 last_auto_nav_time;
    Uint32 auto_nav_interval; // milliseconds
} ImageViewer;

// Function declarations
int is_image_file(const char* filename);
int init_file_list(FileList* list, const char* path);
void cleanup_file_list(FileList* list);
char* get_current_file_path(const FileList* list);
int navigate_to_file(FileList* list, const char* target_filename);
int load_current_image(ImageViewer* viewer);
int navigate_next_image(ImageViewer* viewer);
int navigate_prev_image(ImageViewer* viewer);
void print_current_image_info(const ImageViewer* viewer);
void handle_auto_navigation(ImageViewer* viewer);

int init_viewer(ImageViewer* viewer) {
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL could not initialize! SDL_Error: %s\n", SDL_GetError());
        return 0;
    }

    int img_flags = IMG_INIT_JPG | IMG_INIT_PNG | IMG_INIT_WEBP;
    if (!(IMG_Init(img_flags) & img_flags)) {
        printf("SDL_image could not initialize! SDL_image Error: %s\n", IMG_GetError());
        SDL_Quit();
        return 0;
    }

    viewer->window = SDL_CreateWindow("Image Viewer",
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
    
    // Initialize file list
    viewer->file_list.files = NULL;
    viewer->file_list.count = 0;
    viewer->file_list.current_index = 0;
    viewer->file_list.base_dir[0] = '\0';
    
    // Initialize auto-navigation state
    viewer->left_key_held = 0;
    viewer->right_key_held = 0;
    viewer->last_auto_nav_time = 0;
    viewer->auto_nav_interval = 100;

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
    printf("\n=== Image Viewer Controls ===\n");
    printf("Mouse wheel / +/-: Zoom in/out\n");
    printf("Mouse drag: Pan image\n");
    printf("Left/Right Arrow: Navigate between images\n");
    printf("Hold Left/Right Arrow: Auto-navigate every second\n");
    printf("R: Reset zoom and position\n");
    printf("F: Fit image to window\n");
    printf("H: Show this help\n");
    printf("ESC/Q: Quit\n");
    printf("===============================\n\n");
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
    cleanup_file_list(&viewer->file_list);
    IMG_Quit();
    SDL_Quit();
}

int is_image_file(const char* filename) {
    const char* ext = strrchr(filename, '.');
    if (!ext) return 0;
    
    ext++; // Skip the dot
    return (strcasecmp(ext, "jpg") == 0 || strcasecmp(ext, "jpeg") == 0 ||
            strcasecmp(ext, "png") == 0 || strcasecmp(ext, "bmp") == 0 ||
            strcasecmp(ext, "gif") == 0 || strcasecmp(ext, "tif") == 0 ||
            strcasecmp(ext, "tiff") == 0 || strcasecmp(ext, "webp") == 0);
}

int init_file_list(FileList* list, const char* path) {
    struct stat path_stat;
    list->files = NULL;
    list->count = 0;
    list->current_index = 0;
    
    if (stat(path, &path_stat) != 0) {
        printf("Error: Cannot access path %s\n", path);
        return 0;
    }
    
    if (S_ISDIR(path_stat.st_mode)) {
        // It's a directory - scan for image files
        DIR* dir = opendir(path);
        if (!dir) {
            printf("Error: Cannot open directory %s\n", path);
            return 0;
        }
        
        strcpy(list->base_dir, path);
        
        // First pass: count image files
        struct dirent* entry;
        while ((entry = readdir(dir)) != NULL) {
            if (entry->d_name[0] != '.' && is_image_file(entry->d_name)) {
                // Build full path and check if it's a regular file
                char full_path[MAX_PATH_LEN * 2];
                snprintf(full_path, sizeof(full_path), "%s/%s", path, entry->d_name);
                struct stat file_stat;
                if (stat(full_path, &file_stat) == 0 && S_ISREG(file_stat.st_mode)) {
                    list->count++;
                }
            }
        }
        
        if (list->count == 0) {
            printf("No image files found in directory %s\n", path);
            closedir(dir);
            return 0;
        }
        
        // Allocate memory for file list
        list->files = malloc(list->count * sizeof(char*));
        if (!list->files) {
            printf("Error: Memory allocation failed\n");
            closedir(dir);
            return 0;
        }
        
        // Second pass: store filenames
        rewinddir(dir);
        int index = 0;
        while ((entry = readdir(dir)) != NULL && index < list->count) {
            if (entry->d_name[0] != '.' && is_image_file(entry->d_name)) {
                // Build full path and check if it's a regular file
                char full_path[MAX_PATH_LEN * 2];
                snprintf(full_path, sizeof(full_path), "%s/%s", path, entry->d_name);
                struct stat file_stat;
                if (stat(full_path, &file_stat) == 0 && S_ISREG(file_stat.st_mode)) {
                    list->files[index] = malloc(strlen(entry->d_name) + 1);
                    if (list->files[index]) {
                        strcpy(list->files[index], entry->d_name);
                        index++;
                    }
                }
            }
        }
        list->count = index; // Update count to actual stored files
        
        closedir(dir);
        
        // Sort files alphabetically by filename without extension, shorter names first
        for (int i = 0; i < list->count - 1; i++) {
            for (int j = 0; j < list->count - i - 1; j++) {
                // Extract filenames without extensions
                char name1[MAX_PATH_LEN], name2[MAX_PATH_LEN];
                strcpy(name1, list->files[j]);
                strcpy(name2, list->files[j + 1]);
                
                char* dot1 = strrchr(name1, '.');
                char* dot2 = strrchr(name2, '.');
                if (dot1) *dot1 = '\0';
                if (dot2) *dot2 = '\0';
                
                // Custom comparison: shorter names first, then alphabetical
                int should_swap = 0;
                int len1 = strlen(name1);
                int len2 = strlen(name2);
                
                if (len1 != len2) {
                    // Different lengths - shorter comes first
                    should_swap = (len1 > len2);
                } else {
                    // Same length - alphabetical order
                    should_swap = (strcmp(name1, name2) > 0);
                }
                
                if (should_swap) {
                    char* temp = list->files[j];
                    list->files[j] = list->files[j + 1];
                    list->files[j + 1] = temp;
                }
            }
        }
        
        printf("Found %d image files in directory\n", list->count);
        
    } else if (S_ISREG(path_stat.st_mode)) {
        // It's a single file - scan its directory for all images
        if (!is_image_file(path)) {
            printf("Error: %s is not a supported image file\n", path);
            return 0;
        }
        
        // Extract directory and filename
        char* last_slash = strrchr(path, '/');
        const char* target_filename;
        
        if (last_slash) {
            strncpy(list->base_dir, path, last_slash - path);
            list->base_dir[last_slash - path] = '\0';
            target_filename = last_slash + 1;
        } else {
            strcpy(list->base_dir, ".");
            target_filename = path;
        }
        
        // Now scan the directory for all image files
        DIR* dir = opendir(list->base_dir);
        if (!dir) {
            printf("Error: Cannot open directory %s\n", list->base_dir);
            return 0;
        }
        
        // First pass: count image files in directory
        struct dirent* entry;
        list->count = 0;
        while ((entry = readdir(dir)) != NULL) {
            if (entry->d_name[0] != '.' && is_image_file(entry->d_name)) {
                // Build full path and check if it's a regular file
                char full_path[MAX_PATH_LEN * 2];
                snprintf(full_path, sizeof(full_path), "%s/%s", list->base_dir, entry->d_name);
                struct stat file_stat;
                if (stat(full_path, &file_stat) == 0 && S_ISREG(file_stat.st_mode)) {
                    list->count++;
                }
            }
        }
        
        if (list->count == 0) {
            printf("No image files found in directory %s\n", list->base_dir);
            closedir(dir);
            return 0;
        }
        
        // Allocate memory for file list
        list->files = malloc(list->count * sizeof(char*));
        if (!list->files) {
            printf("Error: Memory allocation failed\n");
            closedir(dir);
            return 0;
        }
        
        // Second pass: store filenames
        rewinddir(dir);
        int index = 0;
        while ((entry = readdir(dir)) != NULL && index < list->count) {
            if (entry->d_name[0] != '.' && is_image_file(entry->d_name)) {
                // Build full path and check if it's a regular file
                char full_path[MAX_PATH_LEN * 2];
                snprintf(full_path, sizeof(full_path), "%s/%s", list->base_dir, entry->d_name);
                struct stat file_stat;
                if (stat(full_path, &file_stat) == 0 && S_ISREG(file_stat.st_mode)) {
                    list->files[index] = malloc(strlen(entry->d_name) + 1);
                    if (list->files[index]) {
                        strcpy(list->files[index], entry->d_name);
                        index++;
                    }
                }
            }
        }
        list->count = index; // Update count to actual stored files
        
        closedir(dir);
        
        // Sort files alphabetically by filename without extension, shorter names first
        for (int i = 0; i < list->count - 1; i++) {
            for (int j = 0; j < list->count - i - 1; j++) {
                // Extract filenames without extensions
                char name1[MAX_PATH_LEN], name2[MAX_PATH_LEN];
                strcpy(name1, list->files[j]);
                strcpy(name2, list->files[j + 1]);
                
                char* dot1 = strrchr(name1, '.');
                char* dot2 = strrchr(name2, '.');
                if (dot1) *dot1 = '\0';
                if (dot2) *dot2 = '\0';
                
                // Custom comparison: shorter names first, then alphabetical
                int should_swap = 0;
                int len1 = strlen(name1);
                int len2 = strlen(name2);
                
                if (len1 != len2) {
                    // Different lengths - shorter comes first
                    should_swap = (len1 > len2);
                } else {
                    // Same length - alphabetical order
                    should_swap = (strcmp(name1, name2) > 0);
                }
                
                if (should_swap) {
                    char* temp = list->files[j];
                    list->files[j] = list->files[j + 1];
                    list->files[j + 1] = temp;
                }
            }
        }
        
        // Find the target file in the sorted list and set current_index
        for (int i = 0; i < list->count; i++) {
            if (strcmp(list->files[i], target_filename) == 0) {
                list->current_index = i;
                break;
            }
        }
        
        printf("Found %d image files in directory, starting with: %s\n", list->count, target_filename);
        
    } else {
        printf("Error: %s is neither a file nor a directory\n", path);
        return 0;
    }
    
    return 1;
}

void cleanup_file_list(FileList* list) {
    if (list->files) {
        for (int i = 0; i < list->count; i++) {
            if (list->files[i]) {
                free(list->files[i]);
            }
        }
        free(list->files);
        list->files = NULL;
    }
    list->count = 0;
    list->current_index = 0;
}

char* get_current_file_path(const FileList* list) {
    if (!list->files || list->current_index < 0 || list->current_index >= list->count) {
        return NULL;
    }
    
    static char full_path[MAX_PATH_LEN * 2];
    snprintf(full_path, sizeof(full_path), "%s/%s", list->base_dir, list->files[list->current_index]);
    return full_path;
}

int navigate_to_file(FileList* list, const char* target_filename) {
    const char* filename = strrchr(target_filename, '/');
    filename = filename ? filename + 1 : target_filename;
    
    for (int i = 0; i < list->count; i++) {
        if (strcmp(list->files[i], filename) == 0) {
            list->current_index = i;
            return 1;
        }
    }
    return 0;
}

int load_current_image(ImageViewer* viewer) {
    char* file_path = get_current_file_path(&viewer->file_list);
    if (!file_path) {
        printf("No current file to load\n");
        return 0;
    }
    
    return load_image(viewer, file_path);
}

int navigate_next_image(ImageViewer* viewer) {
    if (viewer->file_list.count <= 1) return 0;
    
    viewer->file_list.current_index = (viewer->file_list.current_index + 1) % viewer->file_list.count;
    return load_current_image(viewer);
}

int navigate_prev_image(ImageViewer* viewer) {
    if (viewer->file_list.count <= 1) return 0;
    
    viewer->file_list.current_index = (viewer->file_list.current_index - 1 + viewer->file_list.count) % viewer->file_list.count;
    return load_current_image(viewer);
}

void print_current_image_info(const ImageViewer* viewer) {
    if (viewer->file_list.count > 1) {
        printf("Image %d/%d: %s\n", 
               viewer->file_list.current_index + 1, 
               viewer->file_list.count,
               viewer->file_list.files[viewer->file_list.current_index]);
    }
}

void handle_auto_navigation(ImageViewer* viewer) {
    Uint32 current_time = SDL_GetTicks();
    
    if ((viewer->left_key_held || viewer->right_key_held) && 
        (current_time - viewer->last_auto_nav_time >= viewer->auto_nav_interval)) {
        
        if (viewer->left_key_held) {
            if (navigate_prev_image(viewer)) {
                print_current_image_info(viewer);
            }
        } else if (viewer->right_key_held) {
            if (navigate_next_image(viewer)) {
                print_current_image_info(viewer);
            }
        }
        
        viewer->last_auto_nav_time = current_time;
    }
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        printf("Usage: %s <image_file_or_directory>\n", argv[0]);
        printf("Supported formats: JPG, JPEG, PNG, BMP, GIF, TIF, WEBP\n");
        return 1;
    }

    ImageViewer viewer;
    
    if (!init_viewer(&viewer)) {
        printf("Failed to initialize image viewer!\n");
        return 1;
    }

    if (!init_file_list(&viewer.file_list, argv[1])) {
        printf("Failed to initialize file list for: %s\n", argv[1]);
        cleanup_viewer(&viewer);
        return 1;
    }

    if (!load_current_image(&viewer)) {
        printf("Failed to load initial image\n");
        cleanup_viewer(&viewer);
        return 1;
    }

    print_help();
    print_current_image_info(&viewer);

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

                        case SDLK_LEFT:
                            if (!viewer.left_key_held) {
                                // First press - immediate navigation
                                if (navigate_prev_image(&viewer)) {
                                    print_current_image_info(&viewer);
                                }
                                viewer.left_key_held = 1;
                                viewer.last_auto_nav_time = SDL_GetTicks();
                            }
                            break;

                        case SDLK_RIGHT:
                            if (!viewer.right_key_held) {
                                // First press - immediate navigation
                                if (navigate_next_image(&viewer)) {
                                    print_current_image_info(&viewer);
                                }
                                viewer.right_key_held = 1;
                                viewer.last_auto_nav_time = SDL_GetTicks();
                            }
                            break;
                    }
                    break;

                case SDL_KEYUP:
                    switch (e.key.keysym.sym) {
                        case SDLK_LEFT:
                            viewer.left_key_held = 0;
                            break;

                        case SDLK_RIGHT:
                            viewer.right_key_held = 0;
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

        // Handle auto-navigation when keys are held
        handle_auto_navigation(&viewer);

        render_image(&viewer);
        SDL_Delay(16);
    }

    cleanup_viewer(&viewer);
    printf("Image viewer closed.\n");
    return 0;
}