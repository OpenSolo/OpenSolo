#include <gst/gst.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <syslog.h>
#include <stdint.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "80211.h"
#include "INIReader.h"

/* Default defines */
#define DEFAULT_WIDTH 1280
#define DEFAULT_HEIGHT 720
#define DEFAULT_FRAMERATE 24
#define DEFAULT_BITRATE 4000000 // 4mbps

#define ARTOO_IP "10.1.1.1" // Artoo's IP address.
#define IB_PORT 5550        // The in-band video port
#define OOB_PORT 5551       // The oob data port
#define TOS_VO 0xFF         // Max VO bin for the oob port

/* The loop time in us for polling retries, etc */
#define CYCLE_TIME_US 200000

/* Convert seconds to number of loop cycles */
#define SECS_TO_CYCLES(s) (s * 1.e6 / CYCLE_TIME_US)

/* We can currently control one of two things: framerate or bitrate.
 * the vary_framerate switch indicates which one to use.
 */
bool vary_framerate; // Whether or not to vary framerate as the control knob

/* The min/max bitrate and framerate values (come from sololink.conf) */
int min_framerate;
int max_framerate;
int min_bitrate;
int max_bitrate;

/* The step at which the bitrate/framerate should be incremented/decremented
 * per second based on the retry count */
int framerate_step;
int bitrate_step;

/* Variable stream resolution.  This means that the
 * video streamed to the Artoo will vary in width/height based
 * on the input resolution coming from the HDMI input.
 */
bool var_stream_res;

/* Whether or not to crop the recorded 480p resolution */
bool crop_record_res;

/* Pipeline objects */
GstElement *pipeline;
GstElement *source;
GstElement *converter;
GstElement *convcapsfilter;
GstElement *enccapsfilter;
GstElement *encoder;
GstElement *payloader;
GstElement *sink;

/* RTP timestamping */
uint32_t last_timestamp = 0;

/*Struct containing the width/height/fr/br of the stream */
struct vidresfr {
    int width;
    int height;
    int fr;
    int br;
};

/* The input resolution */
struct vidresfr input_res = {DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FRAMERATE, DEFAULT_BITRATE};

/* The streaming resolution */
struct vidresfr stream_res = {DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FRAMERATE, DEFAULT_BITRATE};

/* VBR quant values for 720p and 480p resolutions.
 * This results in roughly 4mbit maxima for both
 * 720p and 480p resolutions, with some extreme bitrates
 * in the 5mbit range.
 */
#define QUANT_720 35
#define QUANT_480 30 // We use this for 576p (PAL) as well.

/* Looks at the input resolution and determines if the
 * stream is NTSC or PAL.  Returns 1 for resolutions
 * greater than or equal to 720, where both NTSC and PAL
 * are the same, other than framerate.
 */
#define IS_NTSC() (input_res.height >= 720 || input_res.height == 480)

/* Looks at the input resolution structure and determines
 * if the input is a recording resolution (480p or 576p).
 */
#define IS_RECORD_RES() (input_res.height < 720)

/* Record the last timestamp from the payloader */
inline void record_last_timestamp(void)
{
    g_object_get(G_OBJECT(payloader), "timestamp", &last_timestamp, NULL);
    syslog(LOG_INFO, "Last timestamp: %u\n", last_timestamp);
}

/*Set the timestamp to last_timestamp in payloader */
inline void set_timestamp(void)
{
    g_object_set(G_OBJECT(payloader), "timestamp-offset", last_timestamp, "config-interval", 1,
                 "pt", 96, NULL);
}

/* Creates a pipeline of the form:
 * mfw_v4l2src ! mfw_ipucsc ! vpuenc ! rtph264pay ! udpsink
 * with default parameters for each
 */
int create_pipeline(void)
{
    /* Build the pipeline */
    pipeline = gst_pipeline_new("video_stream");
    source = gst_element_factory_make("mfw_v4lsrc", "vidsrc");
    convcapsfilter = gst_element_factory_make("capsfilter", NULL);
    converter = gst_element_factory_make("mfw_ipucsc", "converter");
    enccapsfilter = gst_element_factory_make("capsfilter", NULL);
    encoder = gst_element_factory_make("vpuenc", "encoder");
    payloader = gst_element_factory_make("rtph264pay", "payloader");
    sink = gst_element_factory_make("udpsink", "netsink");

    // Make sure they all got created OK
    if (!pipeline || !source || !convcapsfilter || !converter || !enccapsfilter || !encoder ||
        !payloader || !sink) {
        g_printerr("Element(s) could not be created. Exiting.\n");
        return -1;
    }

    /* Set capsfilters for the mfw_ipucsc and vpuenc.
     * If we are in 640x480 input mode, assume the video
     * is cropped down; the GoPro letterboxes the 480p output
     * when recording.  Do this by taking 60 pixels from the top/bottom.
     * Take 72 pixels from top/bottom if its a PAL input.
     * Then, upscale on the output of the ipucsc.
     */
    GstCaps *enccaps;
    if (IS_RECORD_RES() && crop_record_res) {
        enccaps = gst_caps_new_simple("video/x-raw-yuv", "width", G_TYPE_INT, input_res.width,
                                      "height", G_TYPE_INT, input_res.height, "crop-top",
                                      G_TYPE_INT, (IS_NTSC() ? 60 : 72), "crop-bottom", G_TYPE_INT,
                                      (IS_NTSC() ? 60 : 72), NULL);
    } else {
        enccaps = gst_caps_new_simple("video/x-raw-yuv", "width", G_TYPE_INT, input_res.width,
                                      "height", G_TYPE_INT, input_res.height, NULL);
    }
    g_object_set(convcapsfilter, "caps", enccaps, NULL);
    gst_caps_unref(enccaps);

    if (IS_RECORD_RES() && var_stream_res) {
        enccaps = gst_caps_new_simple(
            "video/x-raw-yuv", "format", GST_TYPE_FOURCC, GST_MAKE_FOURCC('I', '4', '2', '0'),
            "width", G_TYPE_INT, stream_res.width,
            /*This next line is ugly but, if the user wants a cropped
             * recording resolution then we handle the cropped stream
             * if it is NTSC or PAL resolution */
            "height", G_TYPE_INT,
            stream_res.height + (crop_record_res ? (IS_NTSC() ? 120 : 144) : 0), NULL);
    } else {
        enccaps = gst_caps_new_simple(
            "video/x-raw-yuv", "format", GST_TYPE_FOURCC, GST_MAKE_FOURCC('I', '4', '2', '0'),
            "width", G_TYPE_INT, stream_res.width, "height", G_TYPE_INT, stream_res.height, NULL);
    }
    g_object_set(enccapsfilter, "caps", enccaps, NULL);
    gst_caps_unref(enccaps);

    /* Set encoder parameters */
    if (vary_framerate) {
        g_object_set(G_OBJECT(encoder), "codec", 6, "framerate-nu", stream_res.fr,
                     "force-framerate", 1, "seqheader-method", 3, "cbr", 0, "quant",
                     (IS_RECORD_RES() ? QUANT_480 : QUANT_720), NULL);
    } else {
        g_object_set(G_OBJECT(encoder), "codec", 6, "framerate-nu", stream_res.fr,
                     "force-framerate", 1, "seqheader-method", 3, "bitrate", (int64_t)stream_res.br,
                     NULL);
    }

    /* Set sink paramters */
    g_object_set(G_OBJECT(sink), "host", ARTOO_IP, "port", IB_PORT, "qos-dscp", 32, NULL);

    /* Set packet type 96
     * NOTE: DO NOT CHANGE PACKET TYPE WITHOUT CONSULTING
     * MOBILE GROUP, SPECIFICALLY JON W.
     *
     * Note: config-interval was previously specified, but it appears
     * that the seqheader-method=3 from vpuenc automatically sends out lots
     * of sps/pps packets.
     */
    g_object_set(G_OBJECT(payloader), "timestamp-offset", last_timestamp, "config-interval", 1,
                 "pt", 96, NULL);

    /* we add all elements into the pipeline */
    gst_bin_add_many(GST_BIN(pipeline), source, convcapsfilter, converter, enccapsfilter, encoder,
                     payloader, sink, NULL);

    /* we link the elements together */
    gst_element_link_many(source, convcapsfilter, converter, enccapsfilter, encoder, payloader,
                          sink, NULL);

    return 0;
}

/* Sets a new framerate for the encoder (vpuenc) and then
 * restarts the pipeline.  This happens very quickly (a couple
 * of frames)
 */
void set_framerate(int fr)
{

    stream_res.fr = fr;

    syslog(LOG_INFO, "New framerate: %ifps", fr);

    record_last_timestamp();

    g_object_set(G_OBJECT(encoder), "framerate-nu", stream_res.fr, "force-framerate", 1, NULL);

    // Restart the pipeline
    gst_element_set_state(pipeline, GST_STATE_NULL);
    gst_element_set_state(pipeline, GST_STATE_READY);
    set_timestamp();
    gst_element_set_state(pipeline, GST_STATE_PLAYING);
}

/* Sets a new bitrate for the encoder (vpuenc) and then
 * restarts the pipeline.
 */
void set_bitrate(int br)
{

    stream_res.br = br;

    syslog(LOG_INFO, "New bitrate: %ibps", br);

    record_last_timestamp();

    g_object_set(G_OBJECT(encoder), "bitrate", br, NULL);

    // Restart the pipeline
    gst_element_set_state(pipeline, GST_STATE_NULL);
    gst_element_set_state(pipeline, GST_STATE_READY);
    set_timestamp();
    gst_element_set_state(pipeline, GST_STATE_PLAYING);
}

/* Shuts down and destroys the pipeline */
int destroy_pipeline(void)
{
    /* Pull off the last timestamp in case the pipeline
     * is being restarted.
     */
    record_last_timestamp();

    gst_element_set_state(pipeline, GST_STATE_NULL);
    g_object_unref(pipeline);
    return 0;
}

/* For catching ctrl+c */
void int_handler(int sig)
{
    destroy_pipeline();
    exit(0);
}

/* Open the out-of-band socket for sending and
 * receiving any out-of-band data, such as a new
 * resolution or an error count.
 */
int open_oob_socket(void)
{
    int fd;
    struct sockaddr_in addr;
    int tos = TOS_VO;

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

    /* Set the socket priority */
    if (setsockopt(fd, IPPROTO_IP, IP_TOS, &tos, sizeof(tos)) < 0)
        return -1;

    fcntl(fd, F_SETFL, O_NONBLOCK); // set to non-blocking

    return fd;
}

/* Send a packet over UDP with the sprop-parameter-sets as
 * its payload.
 */
int send_sprop(int fd)
{
    const gchar *gc;
    struct sockaddr_in addr;
    GstCaps *caps;
    GstStructure *str;
    GstPad *pad;
    int len;

    // Always send to ARTOO's IP on the OOB port.
    memset((char *)&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    inet_aton(ARTOO_IP, &addr.sin_addr);
    addr.sin_port = htons(OOB_PORT);

    /*Attempt to pull of the sprop-parameter-sets from the
     * payloader.  If they're OK, send them along */
    if ((pad = gst_element_get_pad(payloader, "src")) != NULL) {
        if ((caps = GST_PAD_CAPS(pad)) != NULL) {
            if ((str = gst_caps_get_structure(caps, 0)) != NULL) {
                gc = gst_structure_get_string(str, "sprop-parameter-sets");
                if (gc == NULL) {
                    syslog(LOG_ERR, "Unable to get sprop from gstreamer");
                    len = 0;
                } else
                    len = strlen(gc);

                if (len > 0) {
                    if (sendto(fd, (const char *)gc, len, 0, (struct sockaddr *)&addr,
                               sizeof(addr)) < len) {
                        syslog(LOG_ERR, "Unable to send data on OOB port\n");
                        return -1;
                    } else
                        return len;
                }
            }
        }
    }

    /* If we sent -1 bytes its entirely possible that
     * the pipeline did not have a prop to get yet */
    return -1;
}

/* The main routine. Argumenets are only for gstreamer,
 * currently
 */
int main(int argc, char *argv[])
{

    int vid_fd;
    int oob_sock_fd;
    struct v4l2_frmsizeenum sizes;
    uint32_t retries_sec = 0;
    int good_retries = 0;
    int fr;
    int br;

    /* Start the syslog */
    openlog("video", LOG_NDELAY, LOG_LOCAL6);
    syslog(LOG_INFO, "main: built " __DATE__ " " __TIME__);

    /* Get the min/max framerate/bitrate values from sololink.conf */
    INIReader reader("/etc/sololink.conf");

    if (reader.ParseError() < 0) {
        syslog(LOG_ERR, "can't load /etc/sololink.conf");
        return -1;
    }

    min_framerate = reader.GetInteger("video", "videoMinFR", DEFAULT_FRAMERATE);
    max_framerate = reader.GetInteger("video", "videoMaxFR", DEFAULT_FRAMERATE);
    min_bitrate = reader.GetInteger("video", "videoMinBR", DEFAULT_BITRATE);
    max_bitrate = reader.GetInteger("video", "videoMaxBR", DEFAULT_BITRATE);
    framerate_step = reader.GetInteger("video", "videoFRStep", 5);
    bitrate_step = reader.GetInteger("video", "videoBRStep", 500000);
    var_stream_res = reader.GetBoolean("video", "varStreamRes", true);
    crop_record_res = reader.GetBoolean("video", "cropRecordRes", true);

    /* Right now we only support varying framerate or bitrate, not both.
     * Throw an error if all values are different */
    if ((min_framerate != max_framerate) && (min_bitrate != max_bitrate)) {
        syslog(LOG_ERR, "framerate min/max and bitrate min/max are all different");
        return -1;
    }

    /* Check the framerate and bitrate values */
    if (min_framerate < 1 || min_framerate > 60) {
        syslog(LOG_ERR, "minimum framerate is out of bounds (1-60)");
        return -1;
    }
    if (max_framerate < 1 || max_framerate > 60) {
        syslog(LOG_ERR, "maximum framerate is out of bounds (1-60)");
        return -1;
    }
    if (max_framerate < min_framerate) {
        syslog(LOG_ERR, "maximum framerate < min framerate");
        return -1;
    }
    if (min_bitrate < 800000 || min_bitrate > 6000000) {
        syslog(LOG_ERR, "minimum bitrate is out of bounds (800000-6000000)");
        return -1;
    }
    if (max_bitrate < 800000 || max_bitrate > 6000000) {
        syslog(LOG_ERR, "maximum bitrate is out of bounds (800000-6000000)");
        return -1;
    }
    if (max_bitrate < min_bitrate) {
        syslog(LOG_ERR, "maximum bitrate < min bitrate");
        return -1;
    }
    if (framerate_step < 0 || framerate_step > 30) {
        syslog(LOG_ERR, "framerate step is out of bounds (1-30)");
        return -1;
    }
    if (bitrate_step < 100000 || bitrate_step > 2000000) {
        syslog(LOG_ERR, "bitrate step is out of bounds (100000 - 2000000)");
        return -1;
    }

    /* Determine which mode we're in (fixed framerate or fixed bitrate) */
    if (max_framerate == min_framerate) {
        vary_framerate =
            false; // Indicate that we should use CBR but change it based on link conditions
        syslog(LOG_INFO, "Operating in variable bitrate mode (%i-%i)@%ifps", min_bitrate,
               max_bitrate, max_framerate);
    } else if (max_bitrate == min_bitrate) {
        vary_framerate = true; // Indicate that we should use VBR but vary framerate
        syslog(LOG_INFO, "Operating in variable framerate mode (%i-%i)@%ibps", min_framerate,
               max_framerate, max_bitrate);
    }

    /* Mark if we're using a variable stream resolution */
    if (var_stream_res)
        syslog(LOG_INFO, "Using variable streaming resolution");

    /* Only support cropping in variable frame resolution */
    if (!var_stream_res && crop_record_res) {
        syslog(LOG_INFO,
               "WARN: Cropped resolutions only supported in variable streaming resolutions");
        crop_record_res = false;
    }

    /* Set the bitrate/framerates to the set maxima */
    stream_res.fr = max_framerate;
    stream_res.br = max_bitrate;
    fr = max_framerate;
    br = max_bitrate;

    /* sigint handler to destroy the pipeline */
    signal(SIGINT, int_handler);

    /* Modprobe the driver */
    system("modprobe mxc_v4l2_capture");

    /* Initialize GStreamer */
    syslog(LOG_INFO, "Initializing");
    gst_init(&argc, &argv);

    /* Open the oob socket */
    oob_sock_fd = open_oob_socket();
    if (oob_sock_fd <= 0) {
        syslog(LOG_ERR, "Unable to open OOB socket");
        return -1;
    }

    /* Create the pipeline */
    syslog(LOG_INFO, "Creating pipeline");
    if (create_pipeline() < 0)
        return -1;

    /* Start playing */
    syslog(LOG_INFO, "Starting play");
    gst_element_set_state(pipeline, GST_STATE_PLAYING);

    /* Open the video fd for the enum_framesizes ioctl call */
    vid_fd = open("/dev/video0", O_RDWR | O_NONBLOCK, 0);
    if (vid_fd < 0) {
        syslog(LOG_ERR, "Unable to open video device for ioctl");
        destroy_pipeline();
        return -1;
    }

    /* The main loop */
    while (1) {

        /* Check the incoming frame size */
        sizes.index = 0;
        /* Call the ioctl to get the input resolution */
        if (ioctl(vid_fd, VIDIOC_ENUM_FRAMESIZES, &sizes) < 0)
            syslog(LOG_ERR, "Unable to call VIDIOC_ENUM_FRAMESIZES ioctl");
        else {
            if (sizes.discrete.width != (unsigned)input_res.width ||
                sizes.discrete.height != (unsigned)input_res.height) {
                syslog(LOG_INFO, "new size: %ix%i", sizes.discrete.width, sizes.discrete.height);

                /* Set the input size */
                input_res.width = sizes.discrete.width;
                input_res.height = sizes.discrete.height;

                if (var_stream_res) {
                    /* Set the streaming resolution to the incoming size for now */
                    stream_res.width = input_res.width;
                    stream_res.height = input_res.height;
                }

                /* Destroy the pipeline */
                syslog(LOG_INFO, "Restarting pipeline");
                destroy_pipeline();

                /* Re-create the pipeline */
                create_pipeline();

                /* Start playing */
                gst_element_set_state(pipeline, GST_STATE_PLAYING);
            }
        }

        /* Notify the Artoo of the latest resolution.  We do this once per cycle */
        send_sprop(oob_sock_fd);

        /* The framerate/bitrate control is pretty simple.  Any time we see
         *  a retry/sec > 200 we drop the framerate/bitrate by a step.  If its
         *  already at the minimum, we leave it there.  If the retries
         *  are < 200 for 5s we increase the framerate/bitrate by one step up
         *  to the max.
         */
        retries_sec = get_retries() * 1e6 / CYCLE_TIME_US;
        if (retries_sec > 200) {
            /* Reduce the framerate/bitrate by a step if its not already at the
             * minimum value */
            if (vary_framerate && stream_res.fr > min_framerate) {
                fr = stream_res.fr - framerate_step;
                if (fr < min_framerate)
                    fr = min_framerate;
            } else if (!vary_framerate && stream_res.br > min_bitrate) {
                br = stream_res.br - bitrate_step;
                if (br < min_bitrate)
                    br = min_bitrate;
            }
            good_retries = 0;
        }
        /* If the good_retries is not at the max, increment it */
        else if (good_retries < SECS_TO_CYCLES(3)) {
            if (++good_retries >= SECS_TO_CYCLES(3)) {
                /* Increase the framerate/bitrate by a step if its not already at the
                 * maximum value */
                if (vary_framerate && stream_res.fr < max_framerate) {
                    fr = stream_res.fr + 2 * framerate_step;
                    if (fr > max_framerate)
                        fr = max_framerate;
                } else if (!vary_framerate && stream_res.br < max_bitrate) {
                    br = stream_res.br + 2 * bitrate_step;
                    if (br > max_bitrate)
                        br = max_bitrate;
                }
                /* Reset the good retries so we keep counting up */
                good_retries = 0;
            }
        }

        /* Finally, set the actual framerate/bitrate */
        if (vary_framerate && stream_res.fr != fr)
            set_framerate(fr);
        if (!vary_framerate && stream_res.br != br)
            set_bitrate(br);

        usleep(CYCLE_TIME_US);
    }

    /* Should never get here. */

    /* Free resources */
    destroy_pipeline();
    return 0;
}
