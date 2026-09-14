// SPDX-License-Identifier: GPL-2.0-only
/*
 * Logitech G29 + Driving Force Shifter: make 1st and 3rd engage reliably.
 *
 * The wheel firmware decodes the H-shifter's hall-sensor X/Y into gear
 * buttons itself, with thresholds symmetric around Y=125 (top row engages at
 * Y>=~195, releases at Y<=~179). This shifter's neutral sits at Y~105, so the
 * top gates rest at Y 180-193 and only cross the engage line when shoved.
 * Measured 2026-09-11 from raw HID captures; see linux_configuration/docs/DOCS-g29-shifter.md.
 *
 * The bottom row has the same disease in milder form: it rests at Y 30-60,
 * the firmware releases at Y>=~72, and the stick relaxing to Y 58-87 drops
 * 2nd/4th for a second (seen in every baseline capture).
 *
 * This program re-decodes the gears from the raw values with wider
 * hysteresis and ORs the bit into the report before hid-logitech parses it.
 * It never clears anything, so the firmware's own decode cannot regress.
 * 5th (top-right) is left to the firmware: no capture data for that gate.
 *
 * Input report, 12 bytes, no report id:
 *   0-3  hat (4 bits) + 25 buttons; gears 1-6,R = byte 2 bits 0-6
 *   4-5  wheel, 6-8 pedals
 *   9    shifter X (left ~50-90, centre ~105-139, right ~166-191)
 *   10   shifter Y (bottom row ~30-60, neutral ~105, top row ~180-233)
 *   11   flags, 0x40 = stick pushed down (reverse)
 */
#include "vmlinux.h"
#include "hid_bpf.h"
#include "hid_bpf_helpers.h"
#include <bpf/bpf_tracing.h>

#define VID_LOGITECH 0x046D
#define PID_G29_PS3_MODE 0xC24F

HID_BPF_CONFIG(
	HID_DEVICE(BUS_USB, HID_GROUP_ANY, VID_LOGITECH, PID_G29_PS3_MODE)
);

#define REPORT_LEN 12
#define GEAR_BYTE 2
#define GEAR1_BIT 0x01
#define GEAR2_BIT 0x02
#define GEAR3_BIT 0x04
#define GEAR4_BIT 0x08
#define GEAR6_BIT 0x20
#define GEARR_BIT 0x40
#define TOP_BITS (GEAR1_BIT | GEAR3_BIT)
#define RIGHT_BOTTOM_BITS (GEAR6_BIT | GEARR_BIT)
#define SHIFTER_X 9
#define SHIFTER_Y 10
#define FLAGS 11
#define FLAG_DOWN 0x40

/* Calibration (raw 0-255 hall values). Recalibrate by editing these and
 * re-running fix_g29_shifter.sh; g29_shifter_capture.py prints the numbers. */
#define X_LEFT_MAX 96        /* X <= this: left column (1st/2nd) */
#define X_CENTRE_MAX 151     /* X <= this: centre column (3rd/4th); above: right */
#define Y_TOP_ENGAGE 160     /* enter a top gate; firmware needs ~195 */
#define Y_TOP_RELEASE 140    /* leave it; neutral is ~105 so this stays clear */
#define Y_BOTTOM_ENGAGE 65   /* enter a bottom gate; firmware needs ~56 */
#define Y_BOTTOM_RELEASE 85  /* leave it; firmware lets go at ~72 */

/* Hysteresis state: 0 or one gear bit. Persists across reports. */
static __u8 engaged_bit;

/* Gear bit the stick would be in if it were engaged in the given row.
 * Right-bottom is 6th or R depending on whether the stick is pushed down;
 * once engaged there the flag is ignored so a flicker cannot toggle gears. */
static __u8 target_bit(__u8 x, bool top, bool down, __u8 held)
{
	if (x <= X_LEFT_MAX)
		return top ? GEAR1_BIT : GEAR2_BIT;
	if (x <= X_CENTRE_MAX)
		return top ? GEAR3_BIT : GEAR4_BIT;
	if (top)
		return 0; /* 5th: no calibration data, firmware only */
	if (held & RIGHT_BOTTOM_BITS)
		return held;
	return down ? GEARR_BIT : GEAR6_BIT;
}

SEC(HID_BPF_DEVICE_EVENT)
int BPF_PROG(g29_shifter_event, struct hid_bpf_ctx *hctx)
{
	__u8 *data = hid_bpf_get_data(hctx, 0 /* offset */, REPORT_LEN);
	__u8 x, y;
	bool down, top;

	if (!data)
		return 0; /* EPERM check */

	x = data[SHIFTER_X];
	y = data[SHIFTER_Y];
	down = data[FLAGS] & FLAG_DOWN;

	/* Leaving the gate (back towards neutral) or sliding to another column
	 * drops the held gear; a fresh engage is evaluated in the same report. */
	if (engaged_bit) {
		top = engaged_bit & TOP_BITS;
		if ((top ? y < Y_TOP_RELEASE : y > Y_BOTTOM_RELEASE) ||
		    target_bit(x, top, down, engaged_bit) != engaged_bit)
			engaged_bit = 0;
	}
	if (!engaged_bit) {
		if (y >= Y_TOP_ENGAGE)
			engaged_bit = target_bit(x, true, down, 0);
		else if (y <= Y_BOTTOM_ENGAGE)
			engaged_bit = target_bit(x, false, down, 0);
	}

	/* Never contradict the firmware on 6th-vs-R: if it already reports one
	 * of the pair, adding the other would show two gears at once. */
	if ((engaged_bit & RIGHT_BOTTOM_BITS) &&
	    (data[GEAR_BYTE] & RIGHT_BOTTOM_BITS & ~engaged_bit))
		return 0;

	data[GEAR_BYTE] |= engaged_bit;
	return 0;
}

HID_BPF_OPS(g29_shifter) = {
	.hid_device_event = (void *)g29_shifter_event,
};

/* The G29 exposes a second, empty HID interface (.0013 here); only bind to
 * the joystick collection: Usage Page Generic Desktop, Usage Joystick. */
SEC("syscall")
int probe(struct hid_bpf_probe_args *ctx)
{
	if (ctx->rdesc_size > 4 &&
	    ctx->rdesc[0] == 0x05 && ctx->rdesc[1] == 0x01 &&
	    ctx->rdesc[2] == 0x09 && ctx->rdesc[3] == 0x04)
		ctx->retval = 0;
	else
		ctx->retval = -EINVAL;
	return 0;
}

char _license[] SEC("license") = "GPL";
