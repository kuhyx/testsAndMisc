#include <curl/curl.h>
#include <libxml/HTMLparser.h>
#include <libxml/uri.h>
#include <libxml/xpath.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Structure to store downloaded data
struct MemoryStruct
{
    char  *memory;
    size_t size;
};

// Write callback function for curl
static size_t WriteMemoryCallback(void *contents, size_t size, size_t nmemb, void *userp)
{
    size_t               realsize = size * nmemb;
    struct MemoryStruct *mem      = (struct MemoryStruct *)userp;

    char *ptr = realloc(mem->memory, mem->size + realsize + 1);
    if (ptr == NULL)
    {
        printf("Not enough memory!\n");
        return 0;
    }

    mem->memory = ptr;
    memcpy(&(mem->memory[mem->size]), contents, realsize);
    mem->size += realsize;
    mem->memory[mem->size] = 0;

    return realsize;
}

// Initialize the curl request for the URL
CURL *init_curl_request(const char *url, struct MemoryStruct *chunk)
{
    CURL *curl = curl_easy_init();
    if (curl)
    {
        curl_easy_setopt(curl, CURLOPT_URL, url);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteMemoryCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)chunk);
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    }
    return curl;
}

// Download the image file
int download_image(const char *url, const char *image_name)
{
    if (access(image_name, F_OK) != -1)
    {
        printf("Image %s already exists, skipping download.\n", image_name);
        return 0;
    }

    CURL *curl = curl_easy_init();
    if (curl)
    {
        FILE *fp = fopen(image_name, "wb");
        curl_easy_setopt(curl, CURLOPT_URL, url);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, NULL);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, fp);
        CURLcode res = curl_easy_perform(curl);
        fclose(fp);
        curl_easy_cleanup(curl);
        return res == CURLE_OK ? 1 : 0;
    }
    return 0;
}

// Parse HTML and find the XPath expression
xmlChar *get_xpath_value(htmlDocPtr doc, const char *xpathExpr)
{
    xmlXPathContextPtr xpathCtx = xmlXPathNewContext(doc);
    xmlXPathObjectPtr  xpathObj = xmlXPathEvalExpression((xmlChar *)xpathExpr, xpathCtx);
    xmlChar           *result   = NULL;

    if (xpathObj && !xmlXPathNodeSetIsEmpty(xpathObj->nodesetval))
    {
        result = xmlNodeListGetString(doc, xpathObj->nodesetval->nodeTab[0]->xmlChildrenNode, 1);
    }
    xmlXPathFreeObject(xpathObj);
    xmlXPathFreeContext(xpathCtx);
    return result;
}

// Extract the image URL and download it
void extract_and_download_image(htmlDocPtr doc, const char *url)
{
    xmlChar *image_url = get_xpath_value(doc, "//*[@id='cc-comic']/@src");
    if (image_url)
    {
        printf("Found image URL: %s\n", image_url);
        char *image_name = strrchr((char *)image_url, '/');
        if (image_name)
        {
            image_name++; // Skip the '/'
            download_image((char *)image_url, image_name);
        }
        xmlFree(image_url);
    }
}

// Find and return the next button URL
char *find_next_button_url(htmlDocPtr doc)
{
    xmlChar *next_url = get_xpath_value(doc, "//a[contains(@class,'cc-next')]/@href");
    if (next_url)
    {
        char *url_copy = strdup((char *)next_url);
        xmlFree(next_url);
        return url_copy;
    }
    return NULL;
}

// Reset chunk memory size before performing curl request
void reset_chunk_size(struct MemoryStruct *chunk) { chunk->size = 0; }

// Perform curl request and return result
CURLcode perform_curl_request(CURL *curl)
{
    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK)
    {
        printf("curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
    }
    return res;
}

// Parse the HTML document from the chunk memory
htmlDocPtr parse_html_from_chunk(struct MemoryStruct *chunk, const char *url)
{
    return htmlReadMemory(chunk->memory, chunk->size, url, NULL,
                          HTML_PARSE_NOERROR | HTML_PARSE_NOWARNING);
}

// Handle processing of the current HTML document
int process_html_document(htmlDocPtr doc, const char **url)
{
    extract_and_download_image(doc, *url);
    char *next_url = find_next_button_url(doc);

    if (next_url)
    {
        printf("Next URL: %s\n", next_url);
        *url = next_url;
        return 1;
    }
    else
    {
        printf("Reached the end of images.\n");
        return 0;
    }
}

// Clean up resources used during processing
void clean_up(CURL *curl, struct MemoryStruct *chunk)
{
    curl_easy_cleanup(curl);
    free(chunk->memory);
}

// Process the images and follow the next button
void process_images(const char *url)
{
    struct MemoryStruct chunk = {malloc(1), 0};
    CURL               *curl  = init_curl_request(url, &chunk);
    CURLcode            res;

    if (curl)
    {
        do
        {
            reset_chunk_size(&chunk);
            res = perform_curl_request(curl);

            if (res != CURLE_OK)
                break;

            htmlDocPtr doc = parse_html_from_chunk(&chunk, url);
            if (!doc)
                break;

            if (!process_html_document(doc, &url))
                break;

            xmlFreeDoc(doc);
        } while (res == CURLE_OK);

        clean_up(curl, &chunk);
    }
}

int main()
{
    const char *url = "..."; // Replace with your actual URL
    process_images(url);
    printf("All images processed.\n");
    return 0;
}
