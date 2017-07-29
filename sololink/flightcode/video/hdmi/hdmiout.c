#include <gst/gst.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <syslog.h>
#include <netinet/in.h>
#include <arpa/inet.h>

/* For setting the alpha IOCTL */
#define MXCFB_SET_GBL_ALPHA _IOW('F', 0x21, struct mxcfb_gbl_alpha)

#define VID_PORT 5600 // The video port from app_streamer
#define OOB_PORT 5551 // The oob data port

/* Maximum length of an sprop string */
const int sprop_max_len = 256;

GstElement *pipeline;
GstElement *source;
GstElement *depayloader;
GstElement *decoder;
GstElement *sink;

/* Creates a pipeline of the form
 * udpsrc ! rtph264depay ! vpudec ! mfw_isink
 * and initializes all default parameters
 */
int create_pipeline(int port, char *sprop)
{
    /* Build the pipeline */
    pipeline = gst_pipeline_new("video_stream");
    source = gst_element_factory_make("udpsrc", "vidsrc");
    depayloader = gst_element_factory_make("rtph264depay", "depayloader");
    decoder = gst_element_factory_make("vpudec", "decoder");
    sink = gst_element_factory_make("mfw_isink", "sink");

    if (!pipeline || !source || !depayloader || !decoder || !sink) {
        g_printerr("One element could not be created. Exiting.\n");
        return -1;
    }

    /* Caps for the udpsrc.  rtph264depay needs these */
    GstCaps *caps = gst_caps_new_simple("application/x-rtp", "media", G_TYPE_STRING, "video",
                                        "clock-rate", G_TYPE_INT, 90000, "encoding-name",
                                        G_TYPE_STRING, "H264", "sprop-parameter-sets",
                                        G_TYPE_STRING, sprop, "payload", G_TYPE_INT, 96, NULL);

    g_object_set(source, "caps", caps, NULL);
    gst_caps_unref(caps);

    /* Set the udpsrc port */
    g_object_set(G_OBJECT(source), "port", port, NULL);

    /* For non-choppy video output */
    g_object_set(G_OBJECT(decoder), "low-latency", 1, NULL);

    /* we add all elements into the pipeline */
    gst_bin_add_many(GST_BIN(pipeline), source, depayloader, decoder, sink, NULL);

    /* we link the elements together */
    gst_element_link_many(source, depayloader, decoder, sink, NULL);

    return 0;
}

/* destroys the pipeline when shutting down */
int destroy_pipeline(void)
{
    gst_element_set_state(pipeline, GST_STATE_NULL);
    g_object_unref(pipeline);
    return 0;
}

/* Restarts the pipeline without destroying it.  Accepts
 * a new sprop parameter as an arguement.  This assumes
 * the pipeline needs to be restarted but not destroyed when
 * a resolution change occurs to the pipe */
int restart_pipeline(char *sprop)
{
    gst_element_set_state(pipeline, GST_STATE_NULL);

    /* Caps for the udpsrc.  rtph264depay needs these */
    GstCaps *caps = gst_caps_new_simple("application/x-rtp", "media", G_TYPE_STRING, "video",
                                        "clock-rate", G_TYPE_INT, 90000, "encoding-name",
                                        G_TYPE_STRING, "H264", "sprop-parameter-sets",
                                        G_TYPE_STRING, sprop, "payload", G_TYPE_INT, 96, NULL);

    g_object_set(source, "caps", caps, NULL);
    gst_caps_unref(caps);

    gst_element_set_state(pipeline, GST_STATE_READY);
    gst_element_set_state(pipeline, GST_STATE_PLAYING);

    return 0;
}

/* Checks the status of the HDMI connection to
 * determine if we should start or shut down the
 * pipeline
 */
int hdmi_connected(void)
{
    char buf[64];
    memset(buf, 0, 64);

    // Read the cable_state from the sysfs
    int fd =
        open("/sys/devices/soc0/soc.1/20e0000.hdmi_video/cable_state", O_RDONLY | O_NONBLOCK, 0);
    if (fd < 0) {
        syslog(LOG_ERR, "Unable to open cable state file");
        // By default assume its connected
        goto return_connected;
    }

    int len = 0;
    len = read(fd, buf, 64);
    if (len <= 0) {
        syslog(LOG_ERR, "Unable to read cable state file");
        close(fd);
        goto return_connected;
    }

    // Strip the tailing return
    buf[len - 1] = 0;

    if (!strcmp(buf, "plugout")) {
        close(fd);
        return 0;
    } else
        close(fd);

return_connected:
    return 1;
}

/* For handling ctrl-c
*/
void int_handler(int sig)
{
    destroy_pipeline();
    exit(0);
}

/* For setting the vsalpha.  This eliminates the need for
 * a VSALPHA setting in the environment variables, which
 * did not always seem to work
 */
int set_alpha(void)
{
    int fd;
    struct mxcfb_gbl_alpha {
        int enable;
        int alpha;
    } g_alpha;

    g_alpha.alpha = 0; // alpha value
    g_alpha.enable = 1;

    if ((fd = open("/dev/fb0", O_RDWR)) < 0) {
        syslog(LOG_ERR, "Unable to open frame buffer 0");
        return -1;
    }

    if (ioctl(fd, MXCFB_SET_GBL_ALPHA, &g_alpha) < 0) {
        syslog(LOG_ERR, "Set global alpha failed");
        close(fd);
        return -1;
    }

    close(fd);
    return 0;
}

/* Open the out-of-band socket for sending and
 * receiving any out-of-band data, such as a new
 * resolution or an error count.
 */
int open_socket(void)
{
    int fd;
    struct sockaddr_in addr;
    int tos = 0xFF;

    /* create a UDP socket */
    if ((fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0)
        return -1;

    /* Bind the socket to any IP, OOB_PORT */
    memset((char *)&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(OOB_PORT);

    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0)
        return -1;

    /* Set the socket to VI priority */
    if (setsockopt(fd, IPPROTO_IP, IP_TOS, &tos, sizeof(tos)) < 0)
        return -1;

    fcntl(fd, F_SETFL, O_NONBLOCK); // set to non-blocking

    return fd;
}

/* Looks for data on the OOB port.  If available, it
 * returns the width, height and framerate of the
 * stream.
 */
int oob_receive_sprop(int fd, char *sprop)
{
    struct sockaddr_in addr;
    socklen_t addrlen = sizeof(addr);
    char buf[sprop_max_len];
    memset(buf, 0, sprop_max_len);

    int recvlen = recvfrom(fd, buf, sprop_max_len, 0, (struct sockaddr *)&addr, &addrlen);

    if (recvlen > 0) {
        /* Sanity check that we got a null terminated string */
        if (buf[sprop_max_len - 1] != 0) {
            syslog(LOG_INFO, "Got a bad sprop string, ignoring");
            return 0;
        }
        memset(sprop, 0, sprop_max_len);
        strcpy(sprop, buf);
    }

    return recvlen;
}

/* The main entry point.  Arguments are currently only
 * for gstreamer
 */
int main(int argc, char *argv[])
{
    char sprop[sprop_max_len];
    char last_sprop[sprop_max_len];
    memset(sprop, 0, sprop_max_len);
    memset(last_sprop, 0, sprop_max_len);
    int oob_sock_fd;

    /* sig handler to shut down the pipeline */
    signal(SIGINT, int_handler);

    openlog("hdmi", LOG_NDELAY, LOG_LOCAL3);

    /* Set the alphablending off for isink */
    set_alpha();

    /* Sit here and wait until the HDMI is connected */
    syslog(LOG_INFO, "Waiting for an HDMI connection");
    while (!hdmi_connected())
        sleep(1);

    /* Initialize GStreamer */
    syslog(LOG_INFO, "Initializing HDMI pipeline");
    gst_init(&argc, &argv);

    /* Open the oob socket */
    oob_sock_fd = open_socket();
    if (oob_sock_fd <= 0) {
        syslog(LOG_ERR, "Unable to open OOB socket");
        return -1;
    }

    /* Wait for some OOB data */
    while (1) {
        if (oob_receive_sprop(oob_sock_fd, sprop) > 0) {
            syslog(LOG_INFO, "Received sprop");
            break;
        }
        sleep(1);
    }
    memcpy(last_sprop, sprop, sprop_max_len);

    /* Create the pipeline */
    syslog(LOG_INFO, "Creating HDMI pipeline");
    if (create_pipeline(VID_PORT, sprop) < 0)
        return -1;

    /* Start playing */
    syslog(LOG_INFO, "Starting HDMI playing");
    gst_element_set_state(pipeline, GST_STATE_PLAYING);

    // Check the incoming frame size
    while (1) {
        // Check the HDMI connection state
        if (!hdmi_connected()) {
            break; // Exit and let inittab restart us
        }

        // Look for new data on the OOB port
        if (oob_receive_sprop(oob_sock_fd, sprop) > 0) {
            /* If this is a new sprop, restart the pipeline.
             * We are guaranteed to have a null terminated string
             * from the oob_receive_sprop call */
            if (strcmp(sprop, last_sprop) != 0) {
                syslog(LOG_INFO, "Received new sprop: %s", sprop);

                /* Restart the pipeline */
                restart_pipeline(sprop);

                memset(last_sprop, 0, sizeof(last_sprop));
                strcpy(last_sprop, sprop);
            }
        }
        usleep(100000);
    }

    /* Free resources */
    destroy_pipeline();
    close(oob_sock_fd);
    return 0;
}
