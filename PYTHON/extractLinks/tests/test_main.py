from pathlib import Path
import subprocess
import sys

# Allow importing from project root when running pytest from this folder
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "main.py"


def read_lines(p: Path):
    return [l.rstrip("\n") for l in p.read_text(encoding="utf-8").splitlines()]


def test_extract_hosts_function():
    from main import extract_hosts_from_html

    html = (
        '<a href="https://wiby.me/">A</a>'
        '<a href="http://example.com/page">B</a>'
        '<a href="#local">C</a>'
        '<a href="mailto:foo@bar.com">D</a>'
        '<a href="https://wiby.me/about">E</a>'
    )
    hosts = extract_hosts_from_html(html)
    assert hosts == ["wiby.me", "example.com"], hosts


def test_cli_writes_expected_output(tmp_path: Path):
    # copy sample1.html to tmpdir and run the script
    sample = ROOT / "tests" / "sample1.html"
    html_copy = tmp_path / "sample1.html"
    html_copy.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")

    # Run CLI
    out_file = tmp_path / "out.txt"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(html_copy), str(out_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out_file.exists()

    lines = read_lines(out_file)
    # Expected order: first time we see wiby.me, then example.com
    assert lines == ["*wiby.me*", "*example.com*"], lines


def test_cli_default_output_name(tmp_path: Path):
    sample = ROOT / "tests" / "sample2.html"
    html_copy = tmp_path / "sample2.html"
    html_copy.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(html_copy)],
        capture_output=True,
        text=True,
        check=True,
    )

    default_out = tmp_path / "sample2_links.txt"
    assert default_out.exists()

    lines = read_lines(default_out)
    assert lines == ["*sub.domain.co.uk*", "*example.com:8080*"], lines
