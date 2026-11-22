#!/usr/bin/env bats
# game_rec.sh start: which monitor, which audio tracks, which file name.
# Every program it calls is a stub (game_rec_helpers.bash); nothing records.

load game_rec_helpers

setup() {
	setup_stubs
	make_launch_client 4044265
}

teardown() {
	teardown_stubs
}

@test "game on DP-2: exact argv, mic + game + desktop tracks in order" {
	make_reaper 4044284 3347910 "$RAT_EXE"
	set_game_window 109051905 0 0 3840 2160
	rec start
	[ "$status" -eq 0 ]
	assert_argv DP-2 60 rat-game 'Rat Game.exe'
	grep -qxF 'search --onlyvisible --class ^steam_app_3347910$' "$STUB_DIR/xdotool_calls"
}

@test "game window on HDMI-0 records HDMI-0" {
	make_reaper 4044284 3347910 "$RAT_EXE"
	set_game_window 77 3940 100 1280 720
	rec start
	[ "$status" -eq 0 ]
	assert_argv HDMI-0 60 rat-game 'Rat Game.exe'
}

@test "no game window: the focused window's monitor is used" {
	make_reaper 4044284 3347910 "$RAT_EXE"
	set_active_window 88 3840 0 2560 1440
	rec start
	[ "$status" -eq 0 ]
	assert_argv HDMI-0 60 rat-game 'Rat Game.exe'
}

@test "no window found at all: DP-2" {
	make_reaper 4044284 3347910 "$RAT_EXE"
	rec start
	[ "$status" -eq 0 ]
	assert_argv DP-2 60 rat-game 'Rat Game.exe'
}

@test "no Steam game (launch client only): DP-2, no game track" {
	set_active_window 88 3840 0 2560 1440
	rec start
	[ "$status" -eq 0 ]
	assert_argv DP-2 60 desktop
}

@test "game not in --list-application-audio yet: hotkey start names every spelling" {
	make_reaper 4044284 3347910 "$RAT_EXE"
	set_game_window 109051905 0 0 3840 2160
	printf 'vesktop\n' >"$STUB_DIR/apps"
	rec start
	[ "$status" -eq 0 ]
	assert_argv DP-2 60 rat-game 'Rat Game.exe|app:Rat Game'
}

@test "hotkey start retries without the guessed game track if the recorder rejects it" {
	make_reaper 4044284 3347910 "$RAT_EXE"
	printf 'vesktop\n' >"$STUB_DIR/apps"
	export GSR_STUB_REJECT_APP=1 GAME_REC_START_GRACE=0.5
	rec start
	[ "$status" -eq 0 ]
	wait_for_recorder 2
	assert_argv DP-2 60 rat-game
	rec status
	[[ $output != *' auto='* ]]
}

@test "app-audio name matches case-insensitively, list spelling wins" {
	make_reaper 4044284 3347910 "$RAT_EXE"
	set_game_window 109051905 0 0 3840 2160
	printf 'vesktop\nrat game.EXE\n' >"$STUB_DIR/apps"
	rec start
	[ "$status" -eq 0 ]
	assert_argv DP-2 60 rat-game 'rat game.EXE'
}

@test "GAME_REC_MONITOR and GAME_REC_FPS override detection" {
	make_reaper 4044284 3347910 "$RAT_EXE"
	set_game_window 109051905 0 0 3840 2160
	GAME_REC_MONITOR=HDMI-0 GAME_REC_FPS=30 rec start
	[ "$status" -eq 0 ]
	assert_argv HDMI-0 30 rat-game 'Rat Game.exe'
}

@test "output goes under GAME_REC_DIR, created on demand" {
	rec start
	[ "$status" -eq 0 ]
	[ -d "$GAME_REC_DIR" ]
	grep -qx -- "--output=avail -B1 -- $GAME_REC_DIR" "$STUB_DIR/df_calls"
}

@test "app-audio ignores spaces, punctuation and .exe (Oh Deer lists as OhDeer)" {
	make_reaper 4044284 2708450 '/home/kuhy/.local/share/Steam/steamapps/common/Oh Deer/OhDeer.exe'
	printf 'vesktop\nOhDeer\n' >"$STUB_DIR/apps"
	rec start
	[ "$status" -eq 0 ]
	assert_argv DP-2 60 ohdeer OhDeer
}

@test "app-audio also matches the game's Steam directory name" {
	make_reaper 4044284 99 '/home/kuhy/.local/share/Steam/steamapps/common/Some Game/Bin/Win64/SG-Win64-Shipping.exe'
	printf 'vesktop\nsome_game\n' >"$STUB_DIR/apps"
	rec start
	[ "$status" -eq 0 ]
	assert_argv DP-2 60 sg-win64-shipping some_game
}
