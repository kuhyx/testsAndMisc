#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <stdbool.h>
#include <signal.h>

#include "gui.h"
#include "chess.h"
#include "engine.h"
#include "mistakes.h"

typedef struct {
	Position pos;
	Engine engine;
	Gui gui;
	MistakeList mistakes;
	bool replay_mode; // allow revisiting mistakes
	size_t replay_index;
} App;

static void append_uci(char *line, size_t sz, const char *mv){
	if (line[0]) strncat(line, " ", sz-1);
	strncat(line, mv, sz-1);
}

static void position_push_move_text(Position *pos, const Move *m, char *line, size_t lsz){
	(void)pos;
	char u[8]; move_to_uci(m, u);
	append_uci(line, lsz, u);
}

static void collect_all_legal_uci(const Position *pos, char list[][8], size_t *n, size_t max){
	Move mv[MAX_MOVES]; size_t k = chess_generate_legal_moves(pos, mv, MAX_MOVES);
	*n = 0;
	for (size_t i=0;i<k && *n<max;i++){ char u[8]; move_to_uci(&mv[i], u); strncpy(list[(*n)++], u, 8); }
}

static bool uci_in_list(const char *u, char list[][8], size_t n){
	for (size_t i=0;i<n;i++){
		if (strncmp(u, list[i], 8)==0) return true;
	}
	return false;
}

static const char *mistake_file_path(){ return "mistakes.txt"; }

int main(){
	srand((unsigned)time(NULL));

	App app; memset(&app, 0, sizeof(app));
	mistakes_init(&app.mistakes);
	mistakes_load(&app.mistakes, mistake_file_path());

	// Avoid SIGPIPE crashes when engine pipe closes
	signal(SIGPIPE, SIG_IGN);

	if (!gui_init(&app.gui, 720, 760, "Opening Learner")){
		fprintf(stderr, "GUI init failed.\n");
		return 1;
	}

	if (!engine_start(&app.engine)){
		fprintf(stderr, "Error: Neither stockfish nor asmfish found locally. Please install one.\n");
		gui_destroy(&app.gui);
		return 1;
	}

	// Initialize position
	chess_init_start(&app.pos);

	// Randomly pick side
	bool player_is_white = rand()%2==0;
	gui_set_flipped(&app.gui, !player_is_white);

	// gameplay state
	char status[128] = "";
	GuiSelection sel = { .from_sq=-1,.to_sq=-1,.promo=0,.clicked=false };
	char line_uci[512] = ""; // history of moves uci

	// If white, player moves first
	bool awaiting_player = player_is_white;
	char expected_player_move[8] = ""; // best move suggested by engine for player
	bool quit=false;

	while (!quit){
		// Show board
		gui_draw(&app.gui, app.pos.board, &sel, status);

		// Engine to act when it's engine turn
		if (!awaiting_player){
			// 2. Ask engine for proposed responses (5)
			EngineMove props[5]; size_t n = engine_get_top_moves(&app.engine, &app.pos, props, 5);
			// 3. Sort is done in engine; also collect legal ones not proposed
			char legal[256][8]; size_t lcnt=0; collect_all_legal_uci(&app.pos, legal, &lcnt, 256);
			// 4. pick response with decreasing probability
			size_t total = n;
			// add non-proposed at the end with minimal priority
			char pool[300][8]; int weights[300]; size_t pcnt=0;
			for (size_t i=0;i<n;i++){ strncpy(pool[pcnt], props[i].uci, 8); weights[pcnt++] = (int)(n - i); }
			for (size_t i=0;i<lcnt;i++){
				if (!uci_in_list(legal[i], pool, pcnt)) {
					memcpy(pool[pcnt], legal[i], 8);
					pool[pcnt][7] = '\0';
					weights[pcnt++] = 1; total++;
				}
			}
			// weighted pick
			int wsum=0; for (size_t i=0;i<pcnt;i++) wsum += weights[i];
			int r = (wsum>0)? (rand()%wsum) : 0;
			size_t pick=0; for (size_t i=0;i<pcnt;i++){ if (r < weights[i]) { pick=i; break; } r -= weights[i]; }
			// 5. play response
			Move m; if (!parse_uci_move(pool[pick], &app.pos, &m)){ // fallback: best
				if (n>0 && parse_uci_move(props[0].uci, &app.pos, &m)) pick=0; else { snprintf(status, sizeof(status), "No engine move"); quit=true; continue; }
			}
			chess_make_move(&app.pos, &m);
			position_push_move_text(&app.pos, &m, line_uci, sizeof(line_uci));
			awaiting_player = true;
			// 6. Ask engine for optimal response from player
			engine_get_best_move(&app.engine, &app.pos, expected_player_move);
			snprintf(status, sizeof(status), "Your turn");
			continue;
		}

		// Player move input
		int key=0;
		bool updated = gui_poll_move(&app.gui, &sel, &quit, &key);
		if (quit) break;
		if (key=='m' || key=='M'){
			// enter simple replay: load a mistake line and restart from it to the position where best move is required
			if (app.mistakes.count>0){
				if (app.replay_index >= app.mistakes.count) app.replay_index = 0;
				Mistake *mk = &app.mistakes.items[app.replay_index++];
				// reset and play the line moves to reach the mistake position
				chess_init_start(&app.pos);
				char tmp[512]; snprintf(tmp, sizeof(tmp), "%s", mk->line);
				char *tok = strtok(tmp, " ");
				while (tok){ Move m; if (parse_uci_move(tok, &app.pos, &m)) chess_make_move(&app.pos, &m); tok = strtok(NULL, " "); }
				snprintf(status, sizeof(status), "Practice: best is %s", mk->best_move);
				strncpy(expected_player_move, mk->best_move, sizeof(expected_player_move));
				awaiting_player = true;
				gui_set_flipped(&app.gui, !app.pos.white_to_move); // if it's black to move, flip so black bottom
			}
		}
		if (updated && sel.clicked && sel.to_sq>=0){
			Move list[MAX_MOVES]; size_t n = chess_generate_legal_moves(&app.pos, list, MAX_MOVES);
			bool moved=false; Move chosen={0};
			for (size_t i=0;i<n;i++){
				if (list[i].from==sel.from_sq && list[i].to==sel.to_sq){ chosen = list[i]; moved=true; break; }
			}
			sel.clicked=false; sel.from_sq=sel.to_sq=-1; sel.promo=0;
			if (!moved) continue;

			// 7. Compare with expected move
			char uci[8]; move_to_uci(&chosen, uci);
			bool correct = (expected_player_move[0] && strncmp(uci, expected_player_move, 8)==0);
			if (correct){
				chess_make_move(&app.pos, &chosen);
				position_push_move_text(&app.pos, &chosen, line_uci, sizeof(line_uci));
				snprintf(status, sizeof(status), "Correct");
				awaiting_player = false; // engine move next
			} else {
				// log mistake: 1) save all moves that lead to mistake, 2) allow revisit later, 3) reset position
				char fen[256]; chess_to_fen(&app.pos, fen, sizeof(fen));
				mistakes_add(&app.mistakes, fen, expected_player_move, line_uci);
				mistakes_save(&app.mistakes, mistake_file_path());
				snprintf(status, sizeof(status), "Wrong, best was %s", expected_player_move);
				// redo best move to show
				Move best; if (parse_uci_move(expected_player_move, &app.pos, &best)){
					chess_make_move(&app.pos, &best);
					position_push_move_text(&app.pos, &best, line_uci, sizeof(line_uci));
				}
				gui_draw(&app.gui, app.pos.board, &sel, status);
				SDL_Delay(600);
				// reset to start
				chess_init_start(&app.pos);
				line_uci[0]='\0';
				// randomize side again
				player_is_white = rand()%2==0; gui_set_flipped(&app.gui, !player_is_white);
				awaiting_player = player_is_white;
				expected_player_move[0]='\0';
			}
		}

		SDL_Delay(10);
	}

	mistakes_save(&app.mistakes, mistake_file_path());
	gui_destroy(&app.gui);
	engine_stop(&app.engine);
	mistakes_free(&app.mistakes);
	return 0;
}
