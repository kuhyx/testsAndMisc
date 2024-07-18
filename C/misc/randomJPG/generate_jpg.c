#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <jpeglib.h>
#include <sys/stat.h>
#include <errno.h>

typedef struct {
    unsigned char r, g, b;
} RGB;

void print_usage(const char* program_name) {
    printf("Usage: %s [options] <num_images> <size> <block_size> <quality> <output_path> <color1> ... <colorN>\n", program_name);
    printf("Options:\n");
    printf("  -h, --help           Show this help message and exit\n");
    printf("Arguments:\n");
    printf("  <num_images>         Number of images to generate (default: 1)\n");
    printf("  <size>               Size of each image (default: 256)\n");
    printf("  <block_size>         Size of each block (default: 16)\n");
    printf("  <quality>            Quality of the output image (default: 100)\n");
    printf("  <output_path>        Path to save the output image (default: output.png)\n");
    printf("  <color1> ... <colorN> List of colors in hex format (default: #000000 and #FFFFFF)\n");
}

void generate_bloated_jpeg(int size, RGB* color_list, int num_colors, int block_size, const char* output_path, int quality, int image_index, const char* folder) {
    if (size > 1000 || size % block_size != 0) {
        fprintf(stderr, "Size must be 1000 pixels or less and divisible by block_size\n");
        exit(EXIT_FAILURE);
    }

    // Create the folder if it does not exist
    struct stat st = {0};
    if (stat(folder, &st) == -1) {
        if (mkdir(folder, 0700) != 0) {
            fprintf(stderr, "Error creating directory: %s\n", strerror(errno));
            exit(EXIT_FAILURE);
        }
    }

    // Generate unique output path
    char unique_output_path[1024];
    snprintf(unique_output_path, sizeof(unique_output_path), "%s/bloated_image_%d.jpg", folder, image_index);

    // Create the image
    unsigned char *image_buffer = malloc(size * size * 3);
    if (!image_buffer) {
        fprintf(stderr, "Error allocating memory\n");
        exit(EXIT_FAILURE);
    }

    // Fill the image with block_size x block_size pixel squares of random colors from the list
    srand(time(NULL));
    for (int y = 0; y < size; y += block_size) {
        for (int x = 0; x < size; x += block_size) {
            RGB color = color_list[rand() % num_colors];
            for (int i = 0; i < block_size; ++i) {
                for (int j = 0; j < block_size; ++j) {
                    int index = ((y + i) * size + (x + j)) * 3;
                    image_buffer[index] = color.r;
                    image_buffer[index + 1] = color.g;
                    image_buffer[index + 2] = color.b;
                }
            }
        }
    }

    // Save the image as JPEG
    struct jpeg_compress_struct cinfo;
    struct jpeg_error_mgr jerr;

    FILE *outfile = fopen(unique_output_path, "wb");
    if (!outfile) {
        fprintf(stderr, "Error opening output file: %s\n", strerror(errno));
        free(image_buffer);
        exit(EXIT_FAILURE);
    }

    cinfo.err = jpeg_std_error(&jerr);
    jpeg_create_compress(&cinfo);
    jpeg_stdio_dest(&cinfo, outfile);

    cinfo.image_width = size;
    cinfo.image_height = size;
    cinfo.input_components = 3;
    cinfo.in_color_space = JCS_RGB;

    jpeg_set_defaults(&cinfo);
    jpeg_set_quality(&cinfo, quality, TRUE);
    jpeg_start_compress(&cinfo, TRUE);

    JSAMPROW row_pointer;
    while (cinfo.next_scanline < cinfo.image_height) {
        row_pointer = (JSAMPROW) &image_buffer[cinfo.next_scanline * size * 3];
        jpeg_write_scanlines(&cinfo, &row_pointer, 1);
    }

    jpeg_finish_compress(&cinfo);
    fclose(outfile);
    jpeg_destroy_compress(&cinfo);

    free(image_buffer);

    printf("Image %d saved to %s\n", image_index, unique_output_path);
}

int main(int argc, char *argv[]) {
    // Check for help command
    if (argc > 1 && (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0)) {
        print_usage(argv[0]);
        return EXIT_SUCCESS;
    }


    // Default values
    int num_images = 1;
    int size = 256;
    int block_size = 16;
    int quality = 100;
    const char* output_path = "output.png";
    const char* default_colors[] = { "#000000", "#FFFFFF" }; // Example default colors: black and white

    int num_colors = sizeof(default_colors) / sizeof(default_colors[0]);
    RGB* color_list = malloc(num_colors * sizeof(RGB));
    if (!color_list) {
        fprintf(stderr, "Error allocating memory\n");
        return EXIT_FAILURE;
    }

    // Parse the provided arguments
    if (argc > 1) num_images = atoi(argv[1]);
    if (argc > 2) size = atoi(argv[2]);
    if (argc > 3) block_size = atoi(argv[3]);
    if (argc > 4) quality = atoi(argv[4]);
    if (argc > 5) output_path = argv[5];

    // Handle color arguments
    if (argc > 6) {
        num_colors = argc - 6;
        free(color_list); // Free previous allocation
        color_list = malloc(num_colors * sizeof(RGB));
        if (!color_list) {
            fprintf(stderr, "Error allocating memory\n");
            return EXIT_FAILURE;
        }
        for (int i = 0; i < num_colors; ++i) {
            unsigned int r, g, b;
            if (sscanf(argv[6 + i], "#%02x%02x%02x", &r, &g, &b) != 3) {
                fprintf(stderr, "Invalid color format: %s\n", argv[6 + i]);
                free(color_list);
                return EXIT_FAILURE;
            }
            color_list[i] = (RGB) { r, g, b };
        }
    } else {
        // Use default colors if none are provided
        for (int i = 0; i < num_colors; ++i) {
            unsigned int r, g, b;
            if (sscanf(default_colors[i], "#%02x%02x%02x", &r, &g, &b) != 3) {
                fprintf(stderr, "Invalid default color format: %s\n", default_colors[i]);
                free(color_list);
                return EXIT_FAILURE;
            }
            color_list[i] = (RGB) { r, g, b };
        }
    }

    // Create folder named after the current timestamp
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    char folder[64];
    strftime(folder, sizeof(folder) - 1, "generated_images_%Y%m%d_%H%M%S", t);

    for (int i = 1; i <= num_images; ++i) {
        generate_bloated_jpeg(size, color_list, num_colors, block_size, output_path, quality, i, folder);
    }

    free(color_list);
    return EXIT_SUCCESS;
}
