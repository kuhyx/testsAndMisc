// Simple FPS demo using FreeGLUT + legacy OpenGL (compat profile)
// - Move: WASD, Shift to sprint, Space to shoot, Esc to quit
// - Look: mouse
// - Target: red cube; shoot to score and respawn target

#include <GL/glut.h>
#include <GL/glu.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// -------- Math helpers --------
typedef struct { float x, y, z; } vec3;

static inline vec3 v3(float x, float y, float z) { vec3 v = {x,y,z}; return v; }
static inline vec3 v3_add(vec3 a, vec3 b) { return v3(a.x+b.x, a.y+b.y, a.z+b.z); }
static inline vec3 v3_sub(vec3 a, vec3 b) { return v3(a.x-b.x, a.y-b.y, a.z-b.z); }
static inline vec3 v3_scale(vec3 a, float s) { return v3(a.x*s, a.y*s, a.z*s); }
static inline float v3_dot(vec3 a, vec3 b) { return a.x*b.x + a.y*b.y + a.z*b.z; }
static inline vec3 v3_cross(vec3 a, vec3 b) {
	return v3(a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y*b.x);
}
static inline float v3_len(vec3 a) { return sqrtf(v3_dot(a,a)); }
static inline vec3 v3_norm(vec3 a) {
	float l = v3_len(a);
	return l > 1e-6f ? v3_scale(a, 1.0f/l) : v3(0,0,0);
}

// -------- Global state --------
static int g_win_w = 1280, g_win_h = 720;
static bool g_keys[256] = {0};
static bool g_captured_mouse = true;
static int g_last_mouse_x = -1, g_last_mouse_y = -1;
static bool g_ignore_next_passive = false; // avoid warp feedback loops

static vec3 g_cam_pos = {0.0f, 1.6f, 5.0f};
static float g_yaw_deg = -90.0f; // facing -Z initially
static float g_pitch_deg = 0.0f;

static float g_move_speed = 4.0f; // m/s
static float g_sprint_mul = 1.8f;
static float g_mouse_sens = 0.12f; // deg per pixel

typedef struct { vec3 pos; float radius; } Target;
static Target g_target;
static int g_score = 0;

// Bullet visualization
static float g_bullet_t = 0.0f; // seconds left to show bullet line
static vec3 g_bullet_origin, g_bullet_dir;

// Timing
static int g_prev_ms = 0;

// -------- Utility --------
static float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
static float deg2rad(float d) { return d * (float)M_PI / 180.0f; }

static vec3 cam_front()
{
	float yaw = deg2rad(g_yaw_deg);
	float pitch = deg2rad(g_pitch_deg);
	vec3 f = { cosf(pitch)*cosf(yaw), sinf(pitch), cosf(pitch)*sinf(yaw) };
	return v3_norm(f);
}

static vec3 cam_right()
{
	return v3_norm(v3_cross(cam_front(), v3(0,1,0)));
}

static void respawn_target()
{
	float x = ((rand()/(float)RAND_MAX) * 24.0f) - 12.0f; // [-12,12]
	float z = ((rand()/(float)RAND_MAX) * 24.0f) - 12.0f; // [-12,12]
	g_target.pos = v3(x, 0.5f, z);
	g_target.radius = 0.6f; // fits a 1.0 cube roughly
}

// Ray-sphere intersection: returns t >= 0 for first hit, or -1 if miss
static float ray_sphere(vec3 ro, vec3 rd, vec3 c, float r)
{
	vec3 oc = v3_sub(ro, c);
	float b = v3_dot(oc, rd);
	float cterm = v3_dot(oc, oc) - r*r;
	float disc = b*b - cterm;
	if (disc < 0.0f) return -1.0f;
	float t = -b - sqrtf(disc);
	return t >= 0.0f ? t : -1.0f;
}

static void shoot()
{
	vec3 dir = cam_front();
	float t = ray_sphere(g_cam_pos, dir, g_target.pos, g_target.radius);
	g_bullet_origin = g_cam_pos;
	g_bullet_dir = dir;
	g_bullet_t = 0.08f; // show for ~80ms

	if (t >= 0.0f && t < 100.0f) {
		g_score++;
		char title[128];
		snprintf(title, sizeof(title), "FPS Demo | Score: %d", g_score);
		glutSetWindowTitle(title);
		respawn_target();
	}
}

// -------- Rendering --------
static void draw_grid(float half, float step)
{
	glColor3f(0.2f, 0.25f, 0.3f);
	glBegin(GL_LINES);
	for (float x = -half; x <= half + 1e-4f; x += step) {
		glVertex3f(x, 0.0f, -half); glVertex3f(x, 0.0f, half);
	}
	for (float z = -half; z <= half + 1e-4f; z += step) {
		glVertex3f(-half, 0.0f, z); glVertex3f(half, 0.0f, z);
	}
	glEnd();
}

static void draw_cube()
{
	// Simple colored cube (size 1)
	const float s = 0.5f;
	glBegin(GL_QUADS);
	// +X
	glColor3f(1,0,0); glVertex3f( s,-s,-s); glVertex3f( s,-s, s); glVertex3f( s, s, s); glVertex3f( s, s,-s);
	// -X
	glColor3f(0.8f,0,0); glVertex3f(-s,-s,-s); glVertex3f(-s, s,-s); glVertex3f(-s, s, s); glVertex3f(-s,-s, s);
	// +Y
	glColor3f(0.9f,0.1f,0.1f); glVertex3f(-s, s,-s); glVertex3f( s, s,-s); glVertex3f( s, s, s); glVertex3f(-s, s, s);
	// -Y
	glColor3f(0.6f,0.05f,0.05f); glVertex3f(-s,-s,-s); glVertex3f(-s,-s, s); glVertex3f( s,-s, s); glVertex3f( s,-s,-s);
	// +Z
	glColor3f(1,0.2f,0.2f); glVertex3f(-s,-s, s); glVertex3f(-s, s, s); glVertex3f( s, s, s); glVertex3f( s,-s, s);
	// -Z
	glColor3f(0.7f,0.1f,0.1f); glVertex3f(-s,-s,-s); glVertex3f( s,-s,-s); glVertex3f( s, s,-s); glVertex3f(-s, s,-s);
	glEnd();
}

static void draw_crosshair()
{
	glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity();
	gluOrtho2D(0, g_win_w, g_win_h, 0);
	glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity();

	glDisable(GL_DEPTH_TEST);
	glColor3f(0.95f, 0.95f, 0.95f);
	int cx = g_win_w/2, cy = g_win_h/2;
	int s = 8;
	glBegin(GL_LINES);
	glVertex2i(cx - s, cy); glVertex2i(cx + s, cy);
	glVertex2i(cx, cy - s); glVertex2i(cx, cy + s);
	glEnd();
	glEnable(GL_DEPTH_TEST);

	glMatrixMode(GL_MODELVIEW); glPopMatrix();
	glMatrixMode(GL_PROJECTION); glPopMatrix();
}

static void display()
{
	glClearColor(0.05f, 0.06f, 0.08f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();

	vec3 front = cam_front();
	vec3 at = v3_add(g_cam_pos, front);
	gluLookAt(g_cam_pos.x, g_cam_pos.y, g_cam_pos.z,
			  at.x,        at.y,        at.z,
			  0,           1,           0);

	// Ground grid
	draw_grid(40.0f, 1.0f);

	// Target cube
	glPushMatrix();
	glTranslatef(g_target.pos.x, g_target.pos.y, g_target.pos.z);
	draw_cube();
	glPopMatrix();

	// Bullet line
	if (g_bullet_t > 0.0f) {
		glColor3f(1.0f, 1.0f, 0.3f);
		glBegin(GL_LINES);
		vec3 p0 = g_bullet_origin;
		vec3 p1 = v3_add(p0, v3_scale(g_bullet_dir, 100.0f));
		glVertex3f(p0.x, p0.y, p0.z);
		glVertex3f(p1.x, p1.y, p1.z);
		glEnd();
	}

	// Crosshair overlay
	draw_crosshair();

	glutSwapBuffers();
}

// -------- Update/Input --------
static void update(float dt)
{
	float speed = g_move_speed * ((g_keys['\t'] || g_keys['Q'] || g_keys['q']) ? g_sprint_mul : 1.0f); // Tab/Q to sprint
	vec3 f = cam_front(); f.y = 0.0f; f = v3_norm(f);
	vec3 r = cam_right(); r.y = 0.0f; r = v3_norm(r);

	if (g_keys['W'] || g_keys['w']) g_cam_pos = v3_add(g_cam_pos, v3_scale(f, speed*dt));
	if (g_keys['S'] || g_keys['s']) g_cam_pos = v3_sub(g_cam_pos, v3_scale(f, speed*dt));
	if (g_keys['A'] || g_keys['a']) g_cam_pos = v3_sub(g_cam_pos, v3_scale(r, speed*dt));
	if (g_keys['D'] || g_keys['d']) g_cam_pos = v3_add(g_cam_pos, v3_scale(r, speed*dt));

	// Keep feet on ground
	g_cam_pos.y = 1.6f;

	if (g_bullet_t > 0.0f) {
		g_bullet_t -= dt;
		if (g_bullet_t < 0.0f) g_bullet_t = 0.0f;
	}
}

static void idle()
{
	int now = glutGet(GLUT_ELAPSED_TIME);
	if (g_prev_ms == 0) g_prev_ms = now;
	float dt = (now - g_prev_ms) / 1000.0f;
	g_prev_ms = now;

	update(dt);
	glutPostRedisplay();
}

static void reshape(int w, int h)
{
	g_win_w = w > 1 ? w : 1;
	g_win_h = h > 1 ? h : 1;
	glViewport(0, 0, g_win_w, g_win_h);
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	gluPerspective(75.0, (double)g_win_w/(double)g_win_h, 0.05, 500.0);
	glMatrixMode(GL_MODELVIEW);

	if (g_captured_mouse) {
		g_ignore_next_passive = true;
		glutWarpPointer(g_win_w/2, g_win_h/2);
	}
}

static void keyboard_down(unsigned char key, int x, int y)
{
	(void)x; (void)y;
	g_keys[key] = true;
	if (key == 27) { // Esc
		exit(0);
	} else if (key == ' ') {
		shoot();
	} else if (key == 'm' || key == 'M') {
		g_captured_mouse = !g_captured_mouse;
		glutSetCursor(g_captured_mouse ? GLUT_CURSOR_NONE : GLUT_CURSOR_LEFT_ARROW);
		if (g_captured_mouse) {
			g_ignore_next_passive = true;
			glutWarpPointer(g_win_w/2, g_win_h/2);
		}
	}
}

static void keyboard_up(unsigned char key, int x, int y)
{
	(void)x; (void)y;
	g_keys[key] = false;
}

static void mouse_button(int button, int state, int x, int y)
{
	(void)x; (void)y;
	if (button == GLUT_LEFT_BUTTON && state == GLUT_DOWN) {
		shoot();
	}
}

static void passive_motion(int x, int y)
{
	if (!g_captured_mouse) return;

	if (g_ignore_next_passive) { // ignore event caused by warp
		g_ignore_next_passive = false;
		return;
	}

	if (g_last_mouse_x < 0) { g_last_mouse_x = x; g_last_mouse_y = y; }
	int dx = x - g_win_w/2;
	int dy = y - g_win_h/2;

	g_yaw_deg   += dx * g_mouse_sens;
	g_pitch_deg -= dy * g_mouse_sens;
	g_pitch_deg = clampf(g_pitch_deg, -89.0f, 89.0f);

	g_ignore_next_passive = true;
	glutWarpPointer(g_win_w/2, g_win_h/2);
}

// -------- Init --------
static void init_gl()
{
	glEnable(GL_DEPTH_TEST);
	glEnable(GL_CULL_FACE);
	glCullFace(GL_BACK);
	glLineWidth(1.0f);
}

int main(int argc, char** argv)
{
	(void)argv;
	srand((unsigned)time(NULL));
	respawn_target();

	glutInit(&argc, argv);
	glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH);
	glutInitWindowSize(g_win_w, g_win_h);
	glutCreateWindow("FPS Demo | Score: 0");

	init_gl();

	glutDisplayFunc(display);
	glutIdleFunc(idle);
	glutReshapeFunc(reshape);
	glutKeyboardFunc(keyboard_down);
	glutKeyboardUpFunc(keyboard_up);
	glutPassiveMotionFunc(passive_motion);
	glutMouseFunc(mouse_button);

	// Start with mouse captured
	glutSetCursor(GLUT_CURSOR_NONE);
	g_ignore_next_passive = true;
	glutWarpPointer(g_win_w/2, g_win_h/2);

	glutMainLoop();
	return 0;
}
