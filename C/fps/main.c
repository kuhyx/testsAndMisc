// Simple FPS demo using FreeGLUT + legacy OpenGL (compat profile)
// - Move: WASD, Shift to sprint, Space to shoot, Esc to quit
// - Look: mouse
// - Targets: red cubes move toward you; shoot them before they reach you
// - Game over when a target reaches you; final score shown; press R to restart

#include <GL/glut.h>
#include <GL/glu.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <SDL2/SDL.h>

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

typedef struct { vec3 pos; float radius; float speed; } Target;
static const int MAX_TARGETS = 128;
static Target g_targets[128];
static int g_target_count = 0;
static float g_spawn_timer = 0.0f;
static float g_spawn_interval = 1.2f; // seconds
static int g_score = 0;

typedef enum { GAME_RUNNING = 0, GAME_OVER = 1 } GameState;
static GameState g_state = GAME_RUNNING;

// Bullet visualization removed per request

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

// -------- Audio (SDL2) --------
static SDL_AudioDeviceID g_audio_dev = 0;
static SDL_AudioSpec g_audio_have;
static bool g_audio_ok = false;

static void audio_cleanup(void)
{
	if (g_audio_dev) {
		SDL_ClearQueuedAudio(g_audio_dev);
		SDL_CloseAudioDevice(g_audio_dev);
		g_audio_dev = 0;
	}
	if (g_audio_ok) {
		SDL_QuitSubSystem(SDL_INIT_AUDIO);
		g_audio_ok = false;
	}
}

static void audio_init(void)
{
	if (SDL_InitSubSystem(SDL_INIT_AUDIO) != 0) {
		fprintf(stderr, "SDL audio init failed: %s\n", SDL_GetError());
		return;
	}
	SDL_AudioSpec want;
	SDL_zero(want);
	want.freq = 48000;
	want.format = AUDIO_F32SYS;
	want.channels = 1;
	want.samples = 1024;
	g_audio_dev = SDL_OpenAudioDevice(NULL, 0, &want, &g_audio_have, 0);
	if (!g_audio_dev) {
		fprintf(stderr, "SDL_OpenAudioDevice failed: %s\n", SDL_GetError());
		SDL_QuitSubSystem(SDL_INIT_AUDIO);
		return;
	}
	SDL_PauseAudioDevice(g_audio_dev, 0);
	g_audio_ok = true;
	atexit(audio_cleanup);
}

static void audio_queue_samples(const float* data, int frames)
{
	if (!g_audio_ok) return;
	int bytes = frames * (int)sizeof(float);
	SDL_QueueAudio(g_audio_dev, data, bytes);
}

static void audio_play_tone(float freq, float duration, float vol)
{
	if (!g_audio_ok) return;
	int sr = g_audio_have.freq ? g_audio_have.freq : 48000;
	int frames = (int)(duration * sr);
	if (frames <= 0) return;
	float* buf = (float*)malloc((size_t)frames * sizeof(float));
	if (!buf) return;
	float phase = 0.0f;
	float dp = 2.0f * (float)M_PI * freq / (float)sr;
	for (int i=0; i<frames; ++i) {
		float t = (float)i / (float)frames;
		// simple attack/decay envelope
		float env = t < 0.1f ? (t/0.1f) : (1.0f - t);
		if (env < 0.0f) env = 0.0f;
		buf[i] = sinf(phase) * vol * env;
		phase += dp;
	}
	audio_queue_samples(buf, frames);
	free(buf);
}

static void audio_play_sweep(float f0, float f1, float duration, float vol)
{
	if (!g_audio_ok) return;
	int sr = g_audio_have.freq ? g_audio_have.freq : 48000;
	int frames = (int)(duration * sr);
	if (frames <= 0) return;
	float* buf = (float*)malloc((size_t)frames * sizeof(float));
	if (!buf) return;
	float phase = 0.0f;
	for (int i=0; i<frames; ++i) {
		float t = (float)i / (float)frames; // 0..1
		float f = f0 + (f1 - f0) * t;
		float dp = 2.0f * (float)M_PI * f / (float)sr;
		float env = 1.0f - t; // fade out
		buf[i] = sinf(phase) * vol * env;
		phase += dp;
	}
	audio_queue_samples(buf, frames);
	free(buf);
}

static float frand(float a, float b) { return a + (b-a) * (rand()/(float)RAND_MAX); }

static void clear_targets() { g_target_count = 0; }

static void spawn_target()
{
	if (g_target_count >= MAX_TARGETS) return;
	float radius_spawn = frand(22.0f, 34.0f);
	float ang = frand(0.0f, 2.0f*(float)M_PI);
	vec3 p = v3(cosf(ang)*radius_spawn, 0.5f, sinf(ang)*radius_spawn);
	Target t;
	t.pos = p;
	t.radius = 0.6f;
	t.speed = frand(1.4f, 3.2f);
	g_targets[g_target_count++] = t;
}

static void reset_game()
{
	g_score = 0;
	g_spawn_timer = 0.0f;
	g_spawn_interval = 1.2f;
	clear_targets();
	// spawn a few to start
	for (int i = 0; i < 4; ++i) spawn_target();
	g_state = GAME_RUNNING;
	if (g_captured_mouse) {
		g_ignore_next_passive = true;
		glutWarpPointer(g_win_w/2, g_win_h/2);
	}
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
	if (g_state != GAME_RUNNING) return;
	vec3 dir = cam_front();
	float best_t = 1e9f;
	int best_i = -1;
	for (int i = 0; i < g_target_count; ++i) {
		float t = ray_sphere(g_cam_pos, dir, g_targets[i].pos, g_targets[i].radius);
		if (t >= 0.0f && t < best_t) { best_t = t; best_i = i; }
	}
	audio_play_tone(1600.0f, 0.05f, 0.25f); // shoot

	if (best_i >= 0) {
		// remove hit target (swap remove)
		g_targets[best_i] = g_targets[g_target_count-1];
		g_target_count--;
		g_score++;
	audio_play_tone(600.0f, 0.08f, 0.35f); // hit
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

	// Target cubes
	for (int i = 0; i < g_target_count; ++i) {
		glPushMatrix();
		glTranslatef(g_targets[i].pos.x, g_targets[i].pos.y, g_targets[i].pos.z);
		draw_cube();
		glPopMatrix();
	}

	// Bullet line removed

	// Crosshair overlay (only during gameplay)
	if (g_state == GAME_RUNNING) {
		draw_crosshair();
	}

	// Game over overlay text
	if (g_state == GAME_OVER) {
		// Switch to 2D for text
		glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity();
		gluOrtho2D(0, g_win_w, g_win_h, 0);
		glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity();
		glDisable(GL_DEPTH_TEST);

		const char* line1 = "GAME OVER";
		char line2[64]; snprintf(line2, sizeof(line2), "Score: %d", g_score);
		const char* line3 = "Press R to restart or Esc to quit";

		void* font = GLUT_BITMAP_HELVETICA_18;
		int cx = g_win_w/2; int cy = g_win_h/2;
		glColor3f(1,1,1);
		// naive center: estimate width by char count * 9 px
		int w1 = (int)(9 * strlen(line1));
		int w2 = (int)(9 * strlen(line2));
		int w3 = (int)(9 * strlen(line3));

		glRasterPos2i(cx - w1/2, cy - 30);
		for (const char* p=line1; *p; ++p) glutBitmapCharacter(font, *p);
		glRasterPos2i(cx - w2/2, cy - 8);
		for (const char* p=line2; *p; ++p) glutBitmapCharacter(font, *p);
		glRasterPos2i(cx - w3/2, cy + 18);
		for (const char* p=line3; *p; ++p) glutBitmapCharacter(font, *p);

		glEnable(GL_DEPTH_TEST);
		glMatrixMode(GL_MODELVIEW); glPopMatrix();
		glMatrixMode(GL_PROJECTION); glPopMatrix();
	}

	glutSwapBuffers();
}

// -------- Update/Input --------
static void update(float dt)
{
	if (g_state == GAME_RUNNING) {
		float speed = g_move_speed * ((g_keys['\t'] || g_keys['Q'] || g_keys['q']) ? g_sprint_mul : 1.0f); // Tab/Q to sprint
		vec3 f = cam_front(); f.y = 0.0f; f = v3_norm(f);
		vec3 r = cam_right(); r.y = 0.0f; r = v3_norm(r);

		if (g_keys['W'] || g_keys['w']) g_cam_pos = v3_add(g_cam_pos, v3_scale(f, speed*dt));
		if (g_keys['S'] || g_keys['s']) g_cam_pos = v3_sub(g_cam_pos, v3_scale(f, speed*dt));
		if (g_keys['A'] || g_keys['a']) g_cam_pos = v3_sub(g_cam_pos, v3_scale(r, speed*dt));
		if (g_keys['D'] || g_keys['d']) g_cam_pos = v3_add(g_cam_pos, v3_scale(r, speed*dt));

		// Keep feet on ground
		g_cam_pos.y = 1.6f;

		// Move targets toward player and check collision
		for (int i = 0; i < g_target_count; ++i) {
			vec3 to_player = v3_sub(g_cam_pos, g_targets[i].pos);
			to_player.y = 0.0f;
			vec3 dir = v3_norm(to_player);
			g_targets[i].pos = v3_add(g_targets[i].pos, v3_scale(dir, g_targets[i].speed * dt));
			g_targets[i].pos.y = 0.5f;

			float dist2 = to_player.x*to_player.x + to_player.z*to_player.z;
			float reach = (0.6f + g_targets[i].radius);
			if (dist2 <= reach*reach) {
				g_state = GAME_OVER;
				glutSetCursor(GLUT_CURSOR_LEFT_ARROW);
				audio_play_sweep(400.0f, 120.0f, 0.5f, 0.5f); // game over
				break;
			}
		}

		// Spawn new targets over time (slightly accelerate spawn rate)
		g_spawn_timer += dt;
		if (g_spawn_timer >= g_spawn_interval) {
			g_spawn_timer = 0.0f;
			spawn_target();
			g_spawn_interval = fmaxf(0.4f, g_spawn_interval * 0.98f);
		}
	}

	// No bullet tracer timer
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

	if (g_captured_mouse && g_state == GAME_RUNNING) {
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
		if (g_captured_mouse && g_state == GAME_RUNNING) {
			g_ignore_next_passive = true;
			glutWarpPointer(g_win_w/2, g_win_h/2);
		}
	} else if (key == 'r' || key == 'R') {
		if (g_state == GAME_OVER) {
			glutSetCursor(g_captured_mouse ? GLUT_CURSOR_NONE : GLUT_CURSOR_LEFT_ARROW);
			reset_game();
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
	if (!g_captured_mouse || g_state != GAME_RUNNING) return;

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

	glutInit(&argc, argv);
	glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH);
	glutInitWindowSize(g_win_w, g_win_h);
	glutCreateWindow("FPS Demo");

	init_gl();
	audio_init();

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

	reset_game();

	glutMainLoop();
	return 0;
}
