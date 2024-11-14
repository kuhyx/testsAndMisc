#include <libwebsockets.h>
#include <string.h>
#include <signal.h>

static int interrupted;
static struct lws_context *context;

// Callback for WebSocket communication
static int callback_function(struct lws *wsi, enum lws_callback_reasons reason,
                             void *user, void *in, size_t len) {
    switch (reason) {
        case LWS_CALLBACK_CLIENT_ESTABLISHED:
            printf("WebSocket connection established\n");
            break;

        case LWS_CALLBACK_CLIENT_RECEIVE:
            printf("Received data: %s\n", (char *)in);
            break;

        case LWS_CALLBACK_CLIENT_WRITEABLE: {
            const char *msg = "Hello, WebSocket server!";
            unsigned char buf[LWS_PRE + 512];
            size_t msg_len = strlen(msg);
            memcpy(&buf[LWS_PRE], msg, msg_len);
            lws_write(wsi, &buf[LWS_PRE], msg_len, LWS_WRITE_TEXT);
            break;
        }

        case LWS_CALLBACK_CLOSED:
            printf("WebSocket connection closed\n");
            interrupted = 1;
            break;

        default:
            break;
    }
    return 0;
}

// Signal handler for clean exit
static void sigint_handler(int sig) {
    interrupted = 1;
    lws_cancel_service(context);
}

int main(void) {
    struct lws_protocols protocols[] = {
        {
            "ws-protocol",   // Protocol name
            callback_function, // Callback function
            0,               // Per-session data size
            0,
        },
        {NULL, NULL, 0, 0}  // End of list
    };

    struct lws_client_connect_info ccinfo = {0};
    struct lws_context_creation_info info = {0};
    info.port = CONTEXT_PORT_NO_LISTEN;
    info.protocols = protocols;
    info.options = LWS_SERVER_OPTION_DO_SSL_GLOBAL_INIT;

    // Create WebSocket context
    context = lws_create_context(&info);
    if (!context) {
        fprintf(stderr, "Failed to create context\n");
        return -1;
    }

    signal(SIGINT, sigint_handler);

    // Configure connection details
    ccinfo.context = context;
    ccinfo.address = "echo.websocket.org";  // WebSocket server address
    ccinfo.port = 443;                      // Port (for WSS use 443)
    ccinfo.path = "/";                      // Path on the server
    ccinfo.host = lws_canonical_hostname(context);
    ccinfo.origin = "origin";
    ccinfo.protocol = protocols[0].name;
    ccinfo.ssl_connection = LCCSCF_USE_SSL;  // Use SSL for secure WebSocket

    // Initiate the WebSocket connection
    struct lws *wsi = lws_client_connect_via_info(&ccinfo);
    if (!wsi) {
        fprintf(stderr, "Failed to initiate WebSocket connection\n");
        lws_context_destroy(context);
        return -1;
    }

    // Event loop
    while (!interrupted) {
        lws_service(context, 1000);
    }

    // Cleanup
    lws_context_destroy(context);
    printf("Exiting...\n");
    return 0;
}

