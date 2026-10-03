# Null Device Redirector

A context manager that redirects `sys.stdout` and `sys.stderr` to `os.devnull` for the duration of the block and restores the original streams on exit.

```python
from null_device_redirector import suppress_output

with suppress_output():
    print("this goes nowhere")
    print("neither does this", file=__import__("sys").stderr)
print("this prints normally again")
```

## Why this exists

Call third-party code that is noisy on stdout/stderr during setup, import, or teardown, without losing the ability to see your own program's real output. The single deliberate trade-off: this swaps the Python-level `sys.stdout` / `sys.stderr` objects only. It does **not** dup2 file descriptors 1 and 2 at the OS level, so native code that writes directly to fd 1 via `os.write` or C-level `printf` is not suppressed. That narrower scope avoids the failure modes of fd redirection (interaction with subprocess inheritance, restoring a dup'd fd that a child has closed, thread-safety under GIL-free native code) and keeps the implementation correct for the common case: Python-level `print`, `logging.StreamHandler` bound to `sys.stdout`, and library code that respects `sys.stdout`.

## Edge you will hit

If a library caches `sys.stdout` at import time (e.g. `logger = logging.StreamHandler(sys.stdout)` evaluated once when the module loads), replacing `sys.stdout` later will not affect that cached reference. Redirect that handler explicitly, or import the noisy library inside the `with suppress_output():` block so its capture happens while the redirect is active.
