#!/usr/bin/env bash
# Tests for transcribe_venv.sh — venv setup, pip installs and model prep.
#
# No jail: every write goes under $VENV_DIR / $PROJECT_DIR / $MODEL_DIR, all
# pointed at a throwaway dir, and python3/python/pip/espeak/ffmpeg are all
# intercepted by the harness's PATH stub dir.
#
# The assertions are on RECORDED ARGV. Which index a pip install points at is
# the whole behaviour here -- the cu12 wheel index for CUDA, the CPU-only
# torch index for diarization -- and it is invisible to a "pip was called"
# check.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./transcribe_harness.sh
. "$SCRIPT_DIR/transcribe_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# Globals the entry script defines above its source line.
VENV_DIR="$TEST_TMPDIR/venv"
PROJECT_DIR="$TEST_TMPDIR/project"
MODEL_DIR="$TEST_TMPDIR/models"
PY_HELPERS="$TEST_TMPDIR/helpers.py"
PY_RUNNER="$TEST_TMPDIR/runner.py"
OFFLINE=0
FW_DIARIZE=0
mkdir -p "$PROJECT_DIR"

# shellcheck source=../transcribe_venv.sh
. "$TRANSCRIBE_LIB_DIR/transcribe_venv.sh"

# A venv whose activate is a no-op, so `source` succeeds without a real venv.
_t_make_venv() {
	mkdir -p "$VENV_DIR/bin"
	printf '#!/usr/bin/env bash\n:\n' >"$VENV_DIR/bin/activate"
	printf '#!/usr/bin/env bash\nprintf "%%s %%s\\n" "venv-python" "$*" >>"%s/calls.log"\nexit 0\n' \
		"$TEST_TMPDIR" >"$VENV_DIR/bin/python"
	chmod +x "$VENV_DIR/bin/python"
}

# --- setup_venv: creates the venv when absent -------------------------------
_t_stub python3
_t_stub python
_t_reset_calls
_t_make_venv
setup_venv >/dev/null 2>&1
_t_has "$(_t_calls)" 'pip install --upgrade pip wheel setuptools' \
	"setup_venv upgrades pip tooling when online"

# --- setup_venv: creates the venv when the directory does not exist ---------
# python3 -m venv is stubbed, so the fixture recreates what it would have
# produced -- the subject sources $VENV_DIR/bin/activate immediately after.
rm -rf "$VENV_DIR"
cat >"$TEST_TMPDIR/bin/python3" <<'MKVENV'
#!/usr/bin/env bash
printf 'python3 %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
for arg in "$@"; do :; done
mkdir -p "$arg/bin"
printf '#!/usr/bin/env bash\n:\n' >"$arg/bin/activate"
MKVENV
chmod +x "$TEST_TMPDIR/bin/python3"
_t_reset_calls
create_out="$(setup_venv 2>&1)"
_t_has "$create_out" 'Creating venv at' "setup_venv announces creating a missing venv"
_t_has "$(_t_calls)" '-m venv' "setup_venv builds the venv with python3 -m venv"
_t_stub python3
_t_make_venv

# --- setup_venv: offline skips the pip upgrade ------------------------------
_t_reset_calls
(
	OFFLINE=1
	setup_venv
) >/dev/null 2>&1
_t_lacks "$(_t_calls)" 'pip install --upgrade pip' \
	"setup_venv performs no network pip work when offline"

# --- ensure_runner ----------------------------------------------------------
: >"$PY_RUNNER"
runner_rc=0
ensure_runner || runner_rc=$?
_t_eq "0" "$runner_rc" "ensure_runner accepts an existing runner"

rm -f "$PY_RUNNER"
missing_rc=0
(ensure_runner) >/dev/null 2>&1 || missing_rc=$?
_t_eq "3" "$missing_rc" "a missing runner exits 3"
: >"$PY_RUNNER"

# --- install_python_deps: the plain online path -----------------------------
_t_reset_calls
install_python_deps 0 >/dev/null 2>&1
plain_calls="$(_t_calls)"
_t_has "$plain_calls" 'faster-whisper ffmpeg-python' "the base install pulls faster-whisper"
_t_lacks "$plain_calls" 'cu12' "no CUDA wheels are fetched without the nvidia flag"

# --- install_python_deps: the NVIDIA path -----------------------------------
# check-ctranslate2 must FAIL for the cu12 wheel branch to be taken.
printf '#!/usr/bin/env bash\nprintf "%%s %%s\\n" "venv-python" "$*" >>"%s/calls.log"\nexit 1\n' \
	"$TEST_TMPDIR" >"$VENV_DIR/bin/python"
chmod +x "$VENV_DIR/bin/python"
_t_reset_calls
install_python_deps 1 >/dev/null 2>&1
nv_calls="$(_t_calls)"
_t_has "$nv_calls" 'download.opennmt.net/ctranslate2/cu12' \
	"a missing ctranslate2 fetches the cu12 wheel from the OpenNMT index"
_t_has "$nv_calls" 'nvidia-cublas-cu12' "the NVIDIA path installs the cu12 runtime libs"

# --- install_python_deps: offline verifies instead of installing ------------
_t_reset_calls
off_rc=0
(
	OFFLINE=1
	install_python_deps 0
) >/dev/null 2>&1 || off_rc=$?
off_calls="$(_t_calls)"
_t_eq "0" "$off_rc" "offline install_python_deps succeeds when the module check passes"
_t_has "$off_calls" 'check-faster-whisper' "offline mode verifies the module instead of installing"
_t_lacks "$off_calls" 'pip install' "offline mode runs no pip install at all"

# --- install_python_deps: offline with the module missing exits 7 -----------
printf '#!/usr/bin/env bash\nexit 1\n' >"$TEST_TMPDIR/bin/python"
chmod +x "$TEST_TMPDIR/bin/python"
missing_mod_rc=0
(
	OFFLINE=1
	install_python_deps 0
) >/dev/null 2>&1 || missing_mod_rc=$?
_t_eq "7" "$missing_mod_rc" "a missing faster-whisper in offline mode exits 7"
_t_stub python

# --- install_python_deps: diarization adds its own wheels -------------------
_t_reset_calls
(
	FW_DIARIZE=1
	install_python_deps 0
) >/dev/null 2>&1
dia_calls="$(_t_calls)"
_t_has "$dia_calls" 'soundfile speechbrain' "diarization installs soundfile and speechbrain"
_t_has "$dia_calls" 'download.pytorch.org/whl/cpu' \
	"diarization forces the CPU-only torch index to avoid mismatched CUDA builds"

# --- install_python_deps: offline diarization checks its own deps -----------
_t_reset_calls
(
	OFFLINE=1
	FW_DIARIZE=1
	install_python_deps 0
) >/dev/null 2>&1
_t_has "$(_t_calls)" 'check-diarization' \
	"offline diarization verifies its own deps as well as faster-whisper"

# --- install_python_deps: every pip failure is a warning, never fatal -------
# pip failing must not abort the run: the subject deliberately trades a
# degraded install for a hard stop, and each `|| log` is that decision.
cat >"$TEST_TMPDIR/bin/python" <<'FAILPIP'
#!/usr/bin/env bash
printf 'python %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
exit 1
FAILPIP
chmod +x "$TEST_TMPDIR/bin/python"
warn_out="$(
	FW_DIARIZE=1
	install_python_deps 1 2>&1
)" || true
_t_has "$warn_out" 'could not reach cu12 wheel index' "the cu12 wheel failure is warned about"
_t_has "$warn_out" 'failed to install NVIDIA cu12 runtime libs' "the cu12 runtime failure is warned about"
_t_has "$warn_out" 'failed to install soundfile/speechbrain' "the diarization dep failure is warned about"
_t_has "$warn_out" 'failed to install torch/torchaudio' "the torch wheel failure is warned about"
_t_stub python

# --- generate_test_audio: espeak-ng is preferred ----------------------------
# The stub must MATERIALISE the wav, or the -s test fails and the next
# fallback runs -- a record-only stub would silently test the wrong branch.
cat >"$TEST_TMPDIR/bin/espeak-ng" <<'ESPEAK'
#!/usr/bin/env bash
printf 'espeak-ng %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
printf 'RIFFfake' >"$2"
ESPEAK
chmod +x "$TEST_TMPDIR/bin/espeak-ng"
_t_reset_calls
audio_out="$(generate_test_audio 2>/dev/null)"
_t_eq "$PROJECT_DIR/test_fw.wav" "${audio_out##*$'\n'}" "generate_test_audio returns the wav path"
_t_has "$(_t_calls)" 'espeak-ng' "espeak-ng is tried first"

# --- generate_test_audio: falls through to espeak ---------------------------
rm -f "$PROJECT_DIR/test_fw.wav"
printf '#!/usr/bin/env bash\nexit 1\n' >"$TEST_TMPDIR/bin/espeak-ng"
chmod +x "$TEST_TMPDIR/bin/espeak-ng"
cat >"$TEST_TMPDIR/bin/espeak" <<'ESPEAK2'
#!/usr/bin/env bash
printf 'espeak %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
printf 'RIFFfake' >"$2"
ESPEAK2
chmod +x "$TEST_TMPDIR/bin/espeak"
_t_reset_calls
generate_test_audio >/dev/null 2>&1
_t_has "$(_t_calls)" 'espeak ' "a failing espeak-ng falls through to espeak"

# --- generate_test_audio: falls through to the Python stdlib generator ------
rm -f "$PROJECT_DIR/test_fw.wav"
_t_unstub espeak-ng
_t_unstub espeak
cat >"$TEST_TMPDIR/bin/python3" <<'PY3'
#!/usr/bin/env bash
printf 'python3 %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
for arg in "$@"; do
	case "$prev" in --file) printf 'RIFFfake' >"$arg" ;; esac
	prev="$arg"
done
PY3
chmod +x "$TEST_TMPDIR/bin/python3"
_t_reset_calls
generate_test_audio >/dev/null 2>&1
_t_has "$(_t_calls)" 'generate-wav' "with no espeak at all the Python stdlib generator is used"

# --- generate_test_audio: the ffmpeg fallback of last resort ----------------
rm -f "$PROJECT_DIR/test_fw.wav"
_t_stub python3
_t_stub ffmpeg
_t_reset_calls
generate_test_audio >/dev/null 2>&1
_t_has "$(_t_calls)" 'sine=frequency=1000:duration=3' \
	"when every generator fails, ffmpeg synthesises a 1kHz tone"

# --- prepare_model ----------------------------------------------------------
_t_reset_calls
prepare_model "small.en" >/dev/null 2>&1
model_calls="$(_t_calls)"
_t_has "$model_calls" 'prepare-model --model small.en' "prepare_model passes the model name through"
_t_has "$model_calls" "--model-dir $MODEL_DIR" "prepare_model targets the configured model dir"
_t_eq "0" "$([[ -d $MODEL_DIR ]] && echo 0 || echo 1)" "prepare_model creates the model dir"

_t_report "test_transcribe_venv.sh"
