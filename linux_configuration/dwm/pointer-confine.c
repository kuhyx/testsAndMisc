/* pointer-confine.c — trap the X pointer on whichever monitor it is currently
 * on, using XFixes pointer barriers, until this process is killed. Barriers are
 * released automatically on exit (signal handler + X client disconnect). dwm's
 * setfullscreen()/unmanage() hooks start this when a window goes fullscreen
 * (games) and stop it when fullscreen ends, so the cursor cannot slide onto the
 * other monitor mid-game. Barriers block only pointer *crossing* — they do not
 * grab or redirect input, so the game's own mouse handling is unaffected.
 *
 * Build: cc pointer-confine.c -o pointer-confine -lX11 -lXfixes -lXinerama
 */
#include <X11/Xlib.h>
#include <X11/extensions/Xfixes.h>
#include <X11/extensions/Xinerama.h>
#include <signal.h>
#include <stdlib.h>
#include <unistd.h>

static Display *dpy;
static PointerBarrier barrier[4];
static int nbar;

/* Drop the barriers and exit cleanly when dwm signals us (or on Ctrl-C). */
static void
release(int sig)
{
	int i;
	(void)sig;
	for (i = 0; i < nbar; i++)
		XFixesDestroyPointerBarrier(dpy, barrier[i]);
	if (dpy) {
		XFlush(dpy);
		XCloseDisplay(dpy);
	}
	_exit(0);
}

int
main(void)
{
	int evb, erb, n, i;
	Window root, rr, cr;
	int rx, ry, wx, wy;
	unsigned int mask;
	int mx = 0, my = 0, mw = 0, mh = 0, found = 0;
	XineramaScreenInfo *si;

	if (!(dpy = XOpenDisplay(NULL)))
		return 1;
	if (!XFixesQueryExtension(dpy, &evb, &erb))
		return 1;                       /* no XFixes -> nothing we can do */
	root = DefaultRootWindow(dpy);

	/* Where is the pointer right now? */
	if (!XQueryPointer(dpy, root, &rr, &cr, &rx, &ry, &wx, &wy, &mask))
		return 1;

	/* Which Xinerama monitor contains it? */
	if (XineramaIsActive(dpy) && (si = XineramaQueryScreens(dpy, &n))) {
		for (i = 0; i < n; i++) {
			if (rx >= si[i].x_org && rx < si[i].x_org + si[i].width &&
			    ry >= si[i].y_org && ry < si[i].y_org + si[i].height) {
				mx = si[i].x_org; my = si[i].y_org;
				mw = si[i].width;  mh = si[i].height; found = 1;
				break;
			}
		}
		XFree(si);
	}
	if (!found)
		return 0;                       /* single monitor -> nothing to confine */

	/* Four barriers boxing the monitor. directions == 0 blocks crossing both
	 * ways, so the pointer is trapped inside [mx,mx+mw) x [my,my+mh). */
	barrier[0] = XFixesCreatePointerBarrier(dpy, root, mx,      my,      mx,      my + mh, 0, 0, NULL);
	barrier[1] = XFixesCreatePointerBarrier(dpy, root, mx + mw, my,      mx + mw, my + mh, 0, 0, NULL);
	barrier[2] = XFixesCreatePointerBarrier(dpy, root, mx,      my,      mx + mw, my,      0, 0, NULL);
	barrier[3] = XFixesCreatePointerBarrier(dpy, root, mx,      my + mh, mx + mw, my + mh, 0, 0, NULL);
	nbar = 4;
	XFlush(dpy);

	signal(SIGTERM, release);
	signal(SIGINT, release);
	signal(SIGHUP, release);

	for (;;)
		pause();                        /* hold the barriers until killed */
	return 0;
}
