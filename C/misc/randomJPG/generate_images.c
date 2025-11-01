#include <errno.h>
#include <jpeglib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

typedef struct
{
    unsigned char r, g, b;
} RGB;

void print_usage(const char *program_name)
{
    printf("Usage: %s [options] <num_images> <size> <block_size> <quality> <output_path> <format> "
           "<color1> ... <colorN>\n",
           program_name);
    printf("Options:\n");
    printf("  -h, --help           Show this help message and exit\n");
    printf("Arguments:\n");
    printf("  <num_images>         Number of images to generate (default: 1)\n");
    printf("  <size>               Size of each image (default: 1000)\n");
    printf("  <block_size>         Size of each block (default: 25)\n");
    printf("  <quality>            Quality of the output image (default: 100)\n");
    printf("  <output_path>        Path to save the output image (default: output.png)\n");
    printf("  <format>             Output format (jpeg or bmp, default: jpeg)\n");
    printf("  <color1> ... <colorN> List of colors in hex format (default: #000000 and #FFFFFF)\n");
}

void create_folder_if_not_exists(const char *folder)
{
    struct stat st = {0};
    if (stat(folder, &st) == -1)
    {
        if (mkdir(folder, 0700) != 0)
        {
            fprintf(stderr, "Error creating directory: %s\n", strerror(errno));
            exit(EXIT_FAILURE);
        }
    }
}

void generate_image_filename(char *unique_output_path, size_t size, const char *folder,
                             int image_index, const char *format)
{
    snprintf(unique_output_path, size, "%s/bloated_image_%d.%s", folder, image_index, format);
}

unsigned char *allocate_image_buffer(int size)
{
    unsigned char *image_buffer = malloc(size * size * 3);
    if (!image_buffer)
    {
        fprintf(stderr, "Error allocating memory\n");
        exit(EXIT_FAILURE);
    }
    return image_buffer;
}

void fill_image_with_colors(unsigned char *image_buffer, int size, RGB *color_list, int num_colors,
                            int block_size)
{
    for (int y = 0; y < size; y += block_size)
    {
        for (int x = 0; x < size; x += block_size)
        {
            RGB color = color_list[rand() % num_colors];
            for (int i = 0; i < block_size; ++i)
            {
                for (int j = 0; j < block_size; ++j)
                {
                    int index               = ((y + i) * size + (x + j)) * 3;
                    image_buffer[index]     = color.r;
                    image_buffer[index + 1] = color.g;
                    image_buffer[index + 2] = color.b;
                }
            }
        }
    }
}

void handle_error(FILE *outfile, unsigned char *image_buffer)
{
    if (!outfile)
    {
        fprintf(stderr, "Error opening output file: %s\n", strerror(errno));
        free(image_buffer);
        exit(EXIT_FAILURE);
    }
}

void setup_compression(struct jpeg_compress_struct *cinfo, struct jpeg_error_mgr *jerr,
                       FILE *outfile, int size, int quality)
{
    cinfo->err = jpeg_std_error(jerr);
    jpeg_create_compress(cinfo);
    jpeg_stdio_dest(cinfo, outfile);

    cinfo->image_width      = size;
    cinfo->image_height     = size;
    cinfo->input_components = 3;
    cinfo->in_color_space   = JCS_RGB;

    jpeg_set_defaults(cinfo);
    jpeg_set_quality(cinfo, quality, TRUE);
    jpeg_start_compress(cinfo, TRUE);
}

void write_scanlines(struct jpeg_compress_struct *cinfo, unsigned char *image_buffer, int size)
{
    JSAMPROW row_pointer;
    while (cinfo->next_scanline < cinfo->image_height)
    {
        row_pointer = (JSAMPROW)&image_buffer[cinfo->next_scanline * size * 3];
        jpeg_write_scanlines(cinfo, &row_pointer, 1);
    }
}

void finalize_compression(struct jpeg_compress_struct *cinfo, FILE *outfile)
{
    jpeg_finish_compress(cinfo);
    fclose(outfile);
    jpeg_destroy_compress(cinfo);
}

void save_image_as_jpeg(unsigned char *image_buffer, int size, const char *unique_output_path,
                        int quality)
{
    struct jpeg_compress_struct cinfo;
    struct jpeg_error_mgr       jerr;
    FILE                       *outfile = fopen(unique_output_path, "wb");

    handle_error(outfile, image_buffer);
    setup_compression(&cinfo, &jerr, outfile, size, quality);
    write_scanlines(&cinfo, image_buffer, size);
    finalize_compression(&cinfo, outfile);

    free(image_buffer);
}

void save_image_as_bmp(unsigned char *image_buffer, int size, const char *unique_output_path)
{
    FILE *outfile = fopen(unique_output_path, "wb");
    handle_error(outfile, image_buffer);

    // BMP Header
    unsigned char bmpfileheader[14] = {'B', 'M', 0, 0, 0, 0, 0, 0, 0, 0, 54, 0, 0, 0};
    unsigned char bmpinfoheader[40] = {40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 24, 0};
    int           filesize          = 54 + 3 * size * size;

    bmpfileheader[2] = (unsigned char)(filesize);
    bmpfileheader[3] = (unsigned char)(filesize >> 8);
    bmpfileheader[4] = (unsigned char)(filesize >> 16);
    bmpfileheader[5] = (unsigned char)(filesize >> 24);

    bmpinfoheader[4]  = (unsigned char)(size);
    bmpinfoheader[5]  = (unsigned char)(size >> 8);
    bmpinfoheader[6]  = (unsigned char)(size >> 16);
    bmpinfoheader[7]  = (unsigned char)(size >> 24);
    bmpinfoheader[8]  = (unsigned char)(size);
    bmpinfoheader[9]  = (unsigned char)(size >> 8);
    bmpinfoheader[10] = (unsigned char)(size >> 16);
    bmpinfoheader[11] = (unsigned char)(size >> 24);

    fwrite(bmpfileheader, 1, 14, outfile);
    fwrite(bmpinfoheader, 1, 40, outfile);

    // Write image data (in BMP format, rows are bottom to top)
    for (int y = size - 1; y >= 0; y--)
    {
        fwrite(image_buffer + (y * size * 3), 3, size, outfile);
    }

    fclose(outfile);
    free(image_buffer);
}

void generate_bloated_image(int size, RGB *color_list, int num_colors, int block_size,
                            const char *output_path, int quality, int image_index,
                            const char *folder, const char *format)
{
    if (size % block_size != 0)
    {
        fprintf(stderr, "Size must be divisible by block_size\n");
        exit(EXIT_FAILURE);
    }

    create_folder_if_not_exists(folder);

    char unique_output_path[1024];
    generate_image_filename(unique_output_path, sizeof(unique_output_path), folder, image_index,
                            format);

    unsigned char *image_buffer = allocate_image_buffer(size);

    fill_image_with_colors(image_buffer, size, color_list, num_colors, block_size);

    if (strcmp(format, "jpeg") == 0)
    {
        save_image_as_jpeg(image_buffer, size, unique_output_path, quality);
    }
    else if (strcmp(format, "bmp") == 0)
    {
        save_image_as_bmp(image_buffer, size, unique_output_path);
    }
    else
    {
        fprintf(stderr, "Unsupported format: %s\n", format);
        free(image_buffer);
        exit(EXIT_FAILURE);
    }

    printf("Image %d saved to %s\n", image_index, unique_output_path);
}

void allocate_color_list(int num_colors, RGB **color_list)
{
    *color_list = malloc(num_colors * sizeof(RGB));
    if (!(*color_list))
    {
        fprintf(stderr, "Error allocating memory\n");
        exit(EXIT_FAILURE);
    }
}

void parse_single_color(const char *color_str, RGB *color)
{
    unsigned int r, g, b;
    if (sscanf(color_str, "#%02x%02x%02x", &r, &g, &b) != 3)
    {
        fprintf(stderr, "Invalid color format: %s\n", color_str);
        exit(EXIT_FAILURE);
    }
    *color = (RGB){r, g, b};
}

void parse_color_list(int argc, char *argv[], int *num_colors, RGB **color_list)
{
    *num_colors = argc - 7;
    allocate_color_list(*num_colors, color_list);
    for (int i = 0; i < *num_colors; ++i)
    {
        parse_single_color(argv[7 + i], &(*color_list)[i]);
    }
}

void parse_default_colors(int *num_colors, RGB **color_list)
{
    const char *default_colors[] = {"#000000", "#FFFFFF", "#0000FF", "#00FF00",
                                    "#00FFFF", "#FF0000", "#FF00FF", "#FFFF00"};
    *num_colors                  = sizeof(default_colors) / sizeof(default_colors[0]);
    allocate_color_list(*num_colors, color_list);
    for (int i = 0; i < *num_colors; ++i)
    {
        parse_single_color(default_colors[i], &(*color_list)[i]);
    }
}

void parse_colors(int argc, char *argv[], int *num_colors, RGB **color_list)
{
    if (argc > 7)
    {
        parse_color_list(argc, argv, num_colors, color_list);
    }
    else
    {
        parse_default_colors(num_colors, color_list);
    }
}

void parse_arguments(int argc, char *argv[], int *num_images, int *size, int *block_size,
                     int *quality, const char **output_path, const char **format)
{
    // Default values
    *num_images  = 1;
    *size        = 1000;
    *block_size  = 25;
    *quality     = 100;
    *output_path = "output.png";
    *format      = "jpeg";

    if (argc > 1)
        *num_images = atoi(argv[1]);
    if (argc > 2)
        *size = atoi(argv[2]);
    if (argc > 3)
        *block_size = atoi(argv[3]);
    if (argc > 4)
        *quality = atoi(argv[4]);
    if (argc > 5)
        *output_path = argv[5];
    if (argc > 6)
        *format = argv[6];
}

void create_output_folder(char *folder, size_t folder_size)
{
    time_t     now = time(NULL);
    struct tm *t   = localtime(&now);
    strftime(folder, folder_size, "generated_images_%Y%m%d_%H%M%S", t);
}

int handle_help_option(int argc, char *argv[])
{
    if (argc > 1 && (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0))
    {
        print_usage(argv[0]);
        return 1;
    }
    return 0;
}

int main(int argc, char *argv[])
{
    srand(time(NULL));
    if (handle_help_option(argc, argv))
    {
        return EXIT_SUCCESS;
    }

    // Start time measurement
    clock_t start_time = clock();

    int         num_images, size, block_size, quality;
    const char *output_path, *format;
    parse_arguments(argc, argv, &num_images, &size, &block_size, &quality, &output_path, &format);

    RGB *color_list;
    int  num_colors;
    parse_colors(argc, argv, &num_colors, &color_list);

    char folder[64];
    create_output_folder(folder, sizeof(folder));

    for (int i = 1; i <= num_images; ++i)
    {
        generate_bloated_image(size, color_list, num_colors, block_size, output_path, quality, i,
                               folder, format);
    }

    free(color_list);

    // End time measurement
    clock_t end_time       = clock();
    double  execution_time = (double)(end_time - start_time) / CLOCKS_PER_SEC;
    printf("Generated %d images in %f seconds!\n", num_images, execution_time);
    return EXIT_SUCCESS;
}
