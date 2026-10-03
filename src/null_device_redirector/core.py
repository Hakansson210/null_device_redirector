from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import IO, Iterator


@contextmanager
def suppress_output() -> Iterator[None]:
    """Context manager that redirects sys.stdout and sys.stderr to os.devnull.

    The original streams are always restored on exit, including when an
    exception propagates through the body.

    Why os.devnull instead of /dev/null: os.devnull resolves to the correct
    null device on every supported platform (NUL on Windows, /dev/null on
    POSIX), so this function is portable without needing to detect the OS.

    Why open() in text mode ("w") and flush the real streams first:
    sys.stdout/sys.stderr are text-mode objects. Replacing them with another
    text-mode object that wraps a devnull handle is the most direct swap,
    and it keeps the same interface (str writes, text encoding, etc.) so
    Python-level print and logging.StreamHandler continue to work without
    surprising TypeErrors.

      1. CPython's C-level writing code may still hold buffered state in the
         underlying text encoding buffer when the body runs. If we swap in a
         fresh text wrapper without flushing the old one, writes issued during
         the body can be silently discarded if the old stream ever finalizes.
      2. Some native libraries capture the raw fileno() of sys.stdout rather
         than the Python object. A devnull handle exposes a valid fileno() and
         accepts str (because it is a text stream), which covers that case.

    We therefore flush the real streams before replacing them, restore them
    exactly as found, and flush again on exit before closing the devnull
    handle so the restored text streams see a consistent state.

    What this does NOT do: it does not redirect file descriptor 1/2 at the OS
    level (dup2). Libraries that bypass sys.stdout entirely and write to fd 1
    via os.write will still produce output. That is a deliberate scope
    decision — fd redirection is a different tool with different failure modes
    (thread-safety, restoring a closed dup'd fd, interacting badly with
    subprocess inheritance). If you need that, use a dup2-based suppressor
    instead of this one.
    """
    stdout_fileno: object
    stderr_fileno: object
    try:
        stdout_fileno = sys.stdout.fileno()
    except (AttributeError, ValueError, OSError):
        stdout_fileno = None
    try:
        stderr_fileno = sys.stderr.fileno()
    except (AttributeError, ValueError, OSError):
        stderr_fileno = None

    real_stdout: IO[str] = sys.stdout
    real_stderr: IO[str] = sys.stderr

    for stream in (real_stdout, real_stderr):
        try:
            stream.flush()
        except (AttributeError, ValueError, OSError):
            pass

    devnull = open(os.devnull, "w")

    sys.stdout = devnull  # type: ignore[assignment]
    sys.stderr = devnull  # type: ignore[assignment]

    try:
        yield
    finally:
        try:
            sys.stdout.flush()
        except (AttributeError, ValueError, OSError):
            pass
        try:
            sys.stderr.flush()
        except (AttributeError, ValueError, OSError):
            pass

        sys.stdout = real_stdout
        sys.stderr = real_stderr

        try:
            devnull.close()
        except (AttributeError, ValueError, OSError):
            pass
