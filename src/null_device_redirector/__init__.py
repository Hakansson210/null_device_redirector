"""Null Device Redirector: context manager redirecting stdout and stderr to os.devnull."""

from null_device_redirector.core import suppress_output

__all__ = ["suppress_output"]
