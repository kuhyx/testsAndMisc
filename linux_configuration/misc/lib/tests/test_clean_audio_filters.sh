#!/usr/bin/env bash
# Tests for clean_audio_filters.sh — the ffmpeg filter chain for clean_audio.sh.
#
# No jail: the only writes go under $OUT_DIR, pointed at a throwaway dir, and
# ffmpeg is intercepted by the harness's PATH stub dir.
#
# build_filters is asserted on the EXACT filter string it emits. That string
# is the entire product of this lib -- an arnndn chain missing its 48 kHz
# resample, or a preset silently falling through to no dynamics, is a bug that
# only shows up as worse audio, never as an error.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./transcribe_harness.sh
. "$SCRIPT_DIR/transcribe_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# Globals the entry script sets before calling in.
HIGHPASS=80
AFFTDN_NF=-25
AFFTDN_MD=17
LOWPASS=""
PRESET="asr"
SUFFIX="_clean"
OUT_EXT="wav"
OUT_DIR=""
FORCE=false
JOBS=1
RN_MODEL=""
REQUIRE_ML=false
NO_ADVANCED=false
FFMPEG_BIN="ffmpeg"
FFMPEG_LOG=(-hide_banner)
FFMPEG_OVERWRITE=()
use_arnndn=false
afftdn_supports_md=true
supports_wait_n=true

# shellcheck source=../clean_audio_filters.sh
. "$TRANSCRIBE_LIB_DIR/clean_audio_filters.sh"

# --- print_usage ------------------------------------------------------------
usage_out="$(print_usage)"
_t_has "$usage_out" '--allow-fallback' "the usage text documents --allow-fallback"
_t_has "$usage_out" 'asr (default) | podcast | aggressive' "the usage text lists every preset"

# --- require_cmd ------------------------------------------------------------
_t_stub ffmpeg
require_rc=0
require_cmd ffmpeg || require_rc=$?
_t_eq "0" "$require_rc" "require_cmd accepts a command on PATH"

missing_rc=0
(require_cmd definitely-not-a-real-binary) >/dev/null 2>&1 || missing_rc=$?
_t_eq "1" "$missing_rc" "require_cmd exits 1 for a command that is absent"

# --- find_default_rn_model: the env override wins ---------------------------
: >"$TEST_TMPDIR/override.rnnn"
_t_eq "$TEST_TMPDIR/override.rnnn" "$(RNNOISE_MODEL="$TEST_TMPDIR/override.rnnn" find_default_rn_model)" \
	"RNNOISE_MODEL overrides the search when the file exists"

# --- find_default_rn_model: .rnnn is preferred over .nn ---------------------
mkdir -p "$TEST_TMPDIR/models"
: >"$TEST_TMPDIR/models/legacy.nn"
: >"$TEST_TMPDIR/models/modern.rnnn"
_t_eq "$TEST_TMPDIR/models/modern.rnnn" "$(SCRIPT_DIR="$TEST_TMPDIR" find_default_rn_model)" \
	"a .rnnn model is preferred over a legacy .nn"

# --- find_default_rn_model: nothing found -----------------------------------
rm -f "$TEST_TMPDIR/models/legacy.nn" "$TEST_TMPDIR/models/modern.rnnn"
none_rc=0
(SCRIPT_DIR="$TEST_TMPDIR/empty" find_default_rn_model) >/dev/null 2>&1 || none_rc=$?
_t_eq "1" "$none_rc" "find_default_rn_model returns 1 when no model exists anywhere"

# --- build_filters: the default afftdn chain --------------------------------
default_af="$(build_filters)"
_t_has "$default_af" 'highpass=f=80' "the chain starts with the configured highpass"
_t_has "$default_af" 'afftdn=nf=-25:md=17' "afftdn carries both nf and md when md is supported"
_t_has "$default_af" 'alimiter=limit=0.94' "the asr preset adds a limiter and no dynamics"
_t_has "$default_af" 'aresample=16000' "the chain resamples to 16 kHz for ASR"
_t_has "$default_af" 'aformat=channel_layouts=mono:sample_fmts=s16' "the chain ends mono s16"
_t_lacks "$default_af" 'loudnorm' "the asr preset does not apply loudness normalisation"

# --- build_filters: arnndn replaces afftdn ----------------------------------
arnndn_af="$(
	use_arnndn=true
	RN_MODEL="$TEST_TMPDIR/m.rnnn"
	build_filters
)"
_t_has "$arnndn_af" 'aresample=48000' "arnndn is preceded by the 48 kHz resample it requires"
_t_has "$arnndn_af" "arnndn=m=$TEST_TMPDIR/m.rnnn:mix=1.0" "the arnndn filter carries the model path"
_t_lacks "$arnndn_af" 'afftdn' "afftdn is not applied when arnndn is in use"

# --- build_filters: --no-advanced drops md ----------------------------------
plain_af="$(
	NO_ADVANCED=true
	build_filters
)"
_t_has "$plain_af" 'afftdn=nf=-25' "no-advanced still denoises"
_t_lacks "$plain_af" 'md=' "no-advanced omits the md parameter"

# --- build_filters: REQUIRE_ML refuses to fall back -------------------------
require_ml_rc=0
(
	REQUIRE_ML=true
	build_filters
) >/dev/null 2>&1 || require_ml_rc=$?
_t_eq "11" "$require_ml_rc" "requiring RNNoise exits 11 rather than silently using afftdn"

# --- build_filters: an ffmpeg without md support aborts ---------------------
no_md_rc=0
(
	afftdn_supports_md=false
	build_filters
) >/dev/null 2>&1 || no_md_rc=$?
_t_eq "8" "$no_md_rc" "an ffmpeg lacking afftdn md= exits 8 with an upgrade hint"

# --- build_filters: the optional lowpass ------------------------------------
_t_has "$(
	LOWPASS=8000
	build_filters
)" 'lowpass=f=8000' "a configured lowpass is inserted"

# --- build_filters: the podcast and aggressive presets ----------------------
podcast_af="$(
	PRESET=podcast
	build_filters
)"
_t_has "$podcast_af" 'dynaudnorm=f=500:g=5:p=0.1' "the podcast preset applies gentle dynamics"
_t_has "$podcast_af" 'loudnorm=i=-18:lra=9:tp=-2.0' "the podcast preset normalises loudness"

aggressive_af="$(
	PRESET=aggressive
	build_filters
)"
_t_has "$aggressive_af" 'agate=threshold=0.012:ratio=2.5:release=200' "the aggressive preset gates"
_t_has "$aggressive_af" 'dynaudnorm=f=400:g=7:p=0.1' "the aggressive preset uses its own dynaudnorm"

# --- build_filters: an unknown preset adds nothing --------------------------
unknown_af="$(
	PRESET=nonsense
	build_filters
)"
_t_lacks "$unknown_af" 'alimiter' "an unrecognised preset adds no preset filters"
_t_has "$unknown_af" 'aresample=16000' "an unrecognised preset still gets the ASR tail"

# --- make_out_path_for_file -------------------------------------------------
_t_eq "$TEST_TMPDIR/audio_clean.wav" "$(make_out_path_for_file "$TEST_TMPDIR/audio.mp3")" \
	"the output lands beside the input when no out-dir is set"
_t_eq "$TEST_TMPDIR/out/audio_clean.wav" "$(
	OUT_DIR="$TEST_TMPDIR/out"
	make_out_path_for_file "$TEST_TMPDIR/audio.mp3"
)" "an out-dir redirects the output path"

# --- process_one ------------------------------------------------------------
: >"$TEST_TMPDIR/in.wav"
_t_reset_calls
process_one "$TEST_TMPDIR/in.wav" >/dev/null
_t_has "$(_t_calls)" '-c:a pcm_s16le' "a wav output selects the PCM codec"

flac_calls="$(
	OUT_EXT=flac
	_t_reset_calls
	process_one "$TEST_TMPDIR/in.wav" >/dev/null
	_t_calls
)"
_t_has "$flac_calls" '-c:a flac' "a flac output selects the flac codec"

# --- process_one: an existing output is skipped unless forced ---------------
: >"$TEST_TMPDIR/in_clean.wav"
skip_out="$(process_one "$TEST_TMPDIR/in.wav")"
_t_has "$skip_out" 'Skip (exists)' "an existing output is skipped when FORCE is false"

forced_out="$(
	FORCE=true
	process_one "$TEST_TMPDIR/in.wav"
)"
_t_has "$forced_out" 'Cleaning:' "FORCE=true reprocesses an existing output"

# --- run_dir ----------------------------------------------------------------
mkdir -p "$TEST_TMPDIR/empty_dir"
_t_has "$(run_dir "$TEST_TMPDIR/empty_dir")" 'No audio files found' \
	"an empty directory is reported rather than silently doing nothing"

mkdir -p "$TEST_TMPDIR/audio_dir"
: >"$TEST_TMPDIR/audio_dir/one.wav"
: >"$TEST_TMPDIR/audio_dir/two.MP3"
dir_out="$(
	OUT_DIR="$TEST_TMPDIR/dir_out"
	run_dir "$TEST_TMPDIR/audio_dir"
)"
_t_has "$dir_out" 'one.wav' "run_dir processes a .wav"
_t_has "$dir_out" 'two.MP3' "run_dir matches extensions case-insensitively"

# --- run_dir: parallel mode -------------------------------------------------
parallel_out="$(
	OUT_DIR="$TEST_TMPDIR/par_out"
	JOBS=2
	run_dir "$TEST_TMPDIR/audio_dir"
)"
_t_has "$parallel_out" 'Cleaning:' "run_dir still processes files with JOBS=2"

serial_out="$(
	OUT_DIR="$TEST_TMPDIR/ser_out"
	JOBS=2
	supports_wait_n=false
	run_dir "$TEST_TMPDIR/audio_dir"
)"
_t_has "$serial_out" 'Cleaning:' "an ffmpeg without wait -n falls back to serial processing"

_t_report "test_clean_audio_filters.sh"
