"""
Nuitka build script for Bird Detector.

Use the current interpreter to build the desktop app.
Recommended entrypoint:
    uv run python build_nuitka.py
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Pattern, Tuple

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "BirdDetectorApp"
MAIN_SCRIPT = PROJECT_ROOT / "src" / "main.py"
DIST_PATH = PROJECT_ROOT / "dist"
BUILD_PATH = PROJECT_ROOT / "build"

MONITOR_INTERVAL_SECONDS = 2.0
PERCENT_PATTERN = re.compile(r"(\d{1,3}(?:\.\d+)?)%")
PHASE_PATTERNS: Tuple[Tuple[Pattern[str], str], ...] = (
    (re.compile(r"Nuitka-Options", re.IGNORECASE), "Parsing options"),
    (re.compile(r"python compilation", re.IGNORECASE), "Python optimization"),
    (re.compile(r"generating source", re.IGNORECASE), "Generating C source"),
    (re.compile(r"running data composer", re.IGNORECASE), "Composing frozen data"),
    (re.compile(r"running c compilation", re.IGNORECASE), "Compiling C backend"),
    (re.compile(r"nuitka-scons", re.IGNORECASE), "Compiling and linking"),
    (re.compile(r"copying", re.IGNORECASE), "Copying standalone files"),
)


@dataclass
class ProgressState:
    """Thread-safe progress state used by the monitor thread."""

    phase: str = "Initializing build"
    percent: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)

    def update_from_line(self, line: str) -> None:
        """Update phase and percentage using one Nuitka output line."""
        text = line.strip()
        if not text:
            return

        with self.lock:
            for pattern, phase_name in PHASE_PATTERNS:
                if pattern.search(text):
                    self.phase = phase_name
                    break

            match = PERCENT_PATTERN.search(text)
            if match:
                self.percent = f"{match.group(1)}%"

    def snapshot(self) -> Tuple[str, str]:
        """Return a thread-safe (phase, percent) snapshot."""
        with self.lock:
            return self.phase, self.percent


def expected_output_path() -> Path:
    """Return the expected build output path."""
    system = platform.system()
    if system == "Darwin":
        return DIST_PATH / f"{APP_NAME}.app"
    return DIST_PATH / f"{APP_NAME}.dist"


def format_elapsed(seconds: int) -> str:
    """Format elapsed seconds as HH:MM:SS."""
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_memory(megabytes: Optional[float]) -> str:
    """Format memory value in MB or a fallback label."""
    if megabytes is None:
        return "unavailable"
    return f"{megabytes:.1f} MB"


def process_tree_rss_mb(root_pid: int) -> Optional[float]:
    """Return total RSS memory (MB) for a process tree."""
    if psutil is None:
        return None

    try:
        root = psutil.Process(root_pid)
        processes = [root] + root.children(recursive=True)
        rss_bytes = 0
        for process in processes:
            try:
                rss_bytes += process.memory_info().rss
            except Exception:
                continue
        return rss_bytes / (1024 * 1024)
    except Exception:
        return None


def full_clean_enabled() -> bool:
    """Return whether a full clean is requested for this build."""
    return os.environ.get("NUITKA_FULL_CLEAN", "0") == "1"


def recommended_jobs() -> int:
    """Choose a balanced parallel job count for faster compile times."""
    env_value = os.environ.get("NUITKA_JOBS")
    if env_value:
        try:
            parsed = int(env_value)
            if parsed > 0:
                return parsed
        except ValueError:
            print(
                f"Warning: invalid NUITKA_JOBS='{env_value}', fallback to auto-detected value."
            )

    cpu_count = os.cpu_count() or 1
    if psutil is None:
        return max(1, min(cpu_count, 4))

    # Use a memory-aware default to avoid build termination on lower-memory hosts.
    total_gb = psutil.virtual_memory().total / (1024**3)
    if total_gb < 12:
        return max(1, min(cpu_count, 2))
    if total_gb < 24:
        return max(1, min(cpu_count, 4))
    return max(1, min(cpu_count, 8))


def torch_header_exclusion_arguments() -> List[str]:
    """Exclude non-runtime C/C++ headers unless explicitly requested.

    PyTorch wheels carry large development header trees (torch/include/**).
    These files are not needed at runtime for this app and can trigger huge
    file lists and slower/fragile packaging steps.
    """
    if os.environ.get("NUITKA_KEEP_TORCH_HEADERS", "0") == "1":
        return []

    return [
        "--noinclude-data-files=*.h",
        "--noinclude-data-files=*.hpp",
        "--noinclude-data-files=*.hh",
        "--noinclude-data-files=*.hxx",
        "--noinclude-data-files=*.cuh",
    ]


def icon_arguments() -> list[str]:
    """Build platform-specific icon arguments."""
    icons_dir = PROJECT_ROOT / "src" / "resources" / "icons"
    system = platform.system()

    if system == "Darwin":
        icns_path = icons_dir / "app_icon.icns"
        if icns_path.exists():
            return [f"--macos-app-icon={icns_path}"]

        print(
            "Warning: macOS icon not found at src/resources/icons/app_icon.icns, using default app icon."
        )
        return []

    if system == "Windows":
        ico_path = icons_dir / "favicon.ico"
        if ico_path.exists():
            return [f"--windows-icon-from-ico={ico_path}"]

    return []


def clean_previous_builds(full_clean: bool) -> None:
    """Clean output folders.

    Default mode keeps C build caches for faster incremental builds.
    Set NUITKA_FULL_CLEAN=1 to force a complete cleanup.
    """
    targets = [DIST_PATH]
    if full_clean:
        targets.append(BUILD_PATH)

    for path in targets:
        if path.exists():
            shutil.rmtree(path)
            print(f"Deleted '{path.name}' directory.")

    stale_outputs = [
        PROJECT_ROOT / f"{APP_NAME}.dist",
        PROJECT_ROOT / f"{MAIN_SCRIPT.stem}.dist",
    ]
    if full_clean:
        stale_outputs.extend([
            PROJECT_ROOT / f"{APP_NAME}.build",
            PROJECT_ROOT / f"{APP_NAME}.onefile-build",
            PROJECT_ROOT / f"{MAIN_SCRIPT.stem}.build",
            PROJECT_ROOT / f"{MAIN_SCRIPT.stem}.onefile-build",
        ])

    for path in stale_outputs:
        if path.exists():
            shutil.rmtree(path)
            print(f"Deleted stale output '{path.name}'.")


def build_command(jobs: int) -> List[str]:
    """Construct a Nuitka command suitable for this project."""
    command = [
        sys.executable,
        "-m",
        "nuitka",
        str(MAIN_SCRIPT.relative_to(PROJECT_ROOT)),
        "--standalone",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--jobs={jobs}",
        "--lto=no",
        "--enable-plugin=pyqt5",
        "--include-qt-plugins=sensible,styles",
        f"--output-dir={DIST_PATH}",
        f"--output-filename={APP_NAME}",
        "--include-package=bird_detector_app",
        "--include-package=ui",
        "--include-package=utils",
        f"--include-data-dir={PROJECT_ROOT / 'src' / 'resources'}=resources",
        f"--include-data-file={PROJECT_ROOT / 'config.txt'}=config.txt",
    ]

    system = platform.system()
    if system == "Darwin":
        command.extend([
            "--macos-create-app-bundle",
            f"--macos-app-name={APP_NAME}",
        ])
    elif system == "Windows":
        command.append("--windows-disable-console")

    command.extend(icon_arguments())
    command.extend(torch_header_exclusion_arguments())
    return command


def monitor_build_process(
    process: subprocess.Popen,
    state: ProgressState,
    stop_event: threading.Event,
    start_time: float,
) -> None:
    """Emit periodic monitor logs with elapsed time and memory usage."""
    while not stop_event.is_set() and process.poll() is None:
        phase, percent = state.snapshot()
        progress_text = percent if percent else "collecting"
        memory_text = format_memory(process_tree_rss_mb(process.pid))
        elapsed_text = format_elapsed(int(time.time() - start_time))
        print(
            "[Build Monitor]"
            f" elapsed={elapsed_text}"
            f" | memory={memory_text}"
            f" | progress={progress_text}"
            f" | phase={phase}"
        )
        stop_event.wait(MONITOR_INTERVAL_SECONDS)


def run_nuitka_with_live_monitor(command: List[str]) -> subprocess.CompletedProcess:
    """Run Nuitka and stream output while monitor thread reports build health."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJECT_ROOT,
        bufsize=1,
    )

    state = ProgressState()
    stop_event = threading.Event()
    start_time = time.time()
    monitor_thread = threading.Thread(
        target=monitor_build_process,
        args=(process, state, stop_event, start_time),
        daemon=True,
    )
    monitor_thread.start()

    captured_lines: List[str] = []
    assert process.stdout is not None
    try:
        for line in process.stdout:
            print(line, end="")
            captured_lines.append(line)
            state.update_from_line(line)
    finally:
        stop_event.set()
        monitor_thread.join(timeout=1)

    return_code = process.wait()
    combined_output = "".join(captured_lines)
    if return_code != 0:
        raise subprocess.CalledProcessError(
            returncode=return_code,
            cmd=command,
            output=combined_output,
        )

    return subprocess.CompletedProcess(
        args=command,
        returncode=return_code,
        stdout=combined_output,
        stderr="",
    )


def tail_lines(text: str, max_lines: int = 60) -> str:
    """Return the trailing part of a multiline text block."""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


def build_executable() -> None:
    """Run Nuitka packaging."""
    print(f"Starting Nuitka build for '{APP_NAME}' in {PROJECT_ROOT}")
    print(f"Using Python interpreter: {sys.executable}")

    jobs = recommended_jobs()
    full_clean = full_clean_enabled()
    print(
        "Build speed profile:"
        f" jobs={jobs}, lto=no, full_clean={'on' if full_clean else 'off'}"
    )

    clean_previous_builds(full_clean=full_clean)

    command = build_command(jobs=jobs)
    print("\nRunning Nuitka command:")
    print(f"  {' '.join(command)}\n")

    try:
        run_nuitka_with_live_monitor(command)

        print(f"Build successful! Output is located at: {expected_output_path()}")
    except subprocess.CalledProcessError as error:
        print("\n--- Nuitka Build Failed ---")
        output_text = error.output or ""
        if output_text:
            print("Recent build log lines:")
            print(tail_lines(output_text))

        print("\nCheck the missing dependency or resource path reported above.")
    except Exception as error:  # pragma: no cover
        print(f"\nAn unexpected error occurred during the build process: {error}")


if __name__ == "__main__":
    build_executable()
