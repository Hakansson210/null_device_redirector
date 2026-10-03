"""Tests for null_device_redirector.core.suppress_output."""

from __future__ import annotations

import io
import os
import sys
import unittest

from null_device_redirector import suppress_output
from null_device_redirector.core import suppress_output as suppress_output_from_core


class TestSuppressOutput(unittest.TestCase):
    def setUp(self) -> None:
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

    def tearDown(self) -> None:
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

    def test_exported_from_package(self) -> None:
        # Both names must resolve to the same object so the documented API is stable.
        self.assertIs(suppress_output, suppress_output_from_core)

    def test_context_manager_is_a_generator_function(self) -> None:
        # @contextmanager yields once, so the decorated object is a callable
        # whose return value supports the context manager protocol. We check
        # that contract directly instead of asserting on implementation type.
        with suppress_output() as ctx:
            self.assertIsNone(ctx)

    def test_stdout_replaced_inside_body(self) -> None:
        self.assertIs(sys.stdout, self._original_stdout)
        with suppress_output():
            self.assertIsNot(sys.stdout, self._original_stdout)
        self.assertIs(sys.stdout, self._original_stdout)

    def test_stderr_replaced_inside_body(self) -> None:
        self.assertIs(sys.stderr, self._original_stderr)
        with suppress_output():
            self.assertIsNot(sys.stderr, self._original_stderr)
        self.assertIs(sys.stderr, self._original_stderr)

    def test_restored_on_normal_exit(self) -> None:
        with suppress_output():
            pass
        self.assertIs(sys.stdout, self._original_stdout)
        self.assertIs(sys.stderr, self._original_stderr)

    def test_restored_on_exception(self) -> None:
        class _Marker(Exception):
            pass

        with self.assertRaises(_Marker):
            with suppress_output():
                raise _Marker()
        self.assertIs(sys.stdout, self._original_stdout)
        self.assertIs(sys.stderr, self._original_stderr)

    def test_restored_on_break(self) -> None:
        for _ in range(1):
            with suppress_output():
                break
        self.assertIs(sys.stdout, self._original_stdout)
        self.assertIs(sys.stderr, self._original_stderr)

    def test_restored_on_return(self) -> None:
        def _helper() -> str:
            with suppress_output():
                return "done"

        result = _helper()
        self.assertEqual(result, "done")
        self.assertIs(sys.stdout, self._original_stdout)
        self.assertIs(sys.stderr, self._original_stderr)

    def test_nested_blocks_restore_outer_streams(self) -> None:
        # The inner block's restoration must land on the outer block's
        # redirected streams, not the originals, so the outer block still
        # sees suppression until it itself exits.
        with suppress_output():
            outer_stdout = sys.stdout
            with suppress_output():
                self.assertIsNot(sys.stdout, outer_stdout)
                self.assertIsNot(sys.stdout, self._original_stdout)
            self.assertIs(sys.stdout, outer_stdout)
            self.assertIsNot(sys.stdout, self._original_stdout)
        self.assertIs(sys.stdout, self._original_stdout)

    def test_print_does_not_raise_inside_body(self) -> None:
        with suppress_output():
            print("to stdout")
            print("to stderr", file=sys.stderr)
        # Reaching here means no exception escaped; restoration is checked
        # by the previous tests.

    def test_writes_to_devnull_do_not_reach_real_stdout(self) -> None:
        real_captured = io.StringIO()
        sys.stdout = real_captured
        try:
            with suppress_output():
                print("should vanish")
            # After exit sys.stdout is the stream we set before the block.
            print("should survive")
        finally:
            sys.stdout = self._original_stdout

        self.assertNotIn("should vanish", real_captured.getvalue())
        self.assertIn("should survive", real_captured.getvalue())

    def test_writes_to_devnull_do_not_reach_real_stderr(self) -> None:
        real_captured = io.StringIO()
        sys.stderr = real_captured
        try:
            with suppress_output():
                print("should vanish", file=sys.stderr)
            print("should survive", file=sys.stderr)
        finally:
            sys.stderr = self._original_stderr

        self.assertNotIn("should vanish", real_captured.getvalue())
        self.assertIn("should survive", real_captured.getvalue())

    def test_stream_without_fileno_does_not_crash(self) -> None:
        # StringIO has no fileno(); the implementation must not assume one exists
        # when it flushes the original streams before swapping.
        stream_without_fileno = io.StringIO()
        sys.stdout = stream_without_fileno
        try:
            with suppress_output():
                print("ignored")
            self.assertIs(sys.stdout, stream_without_fileno)
        finally:
            sys.stdout = self._original_stdout

    def test_repeated_use_is_stable(self) -> None:
        for _ in range(5):
            with suppress_output():
                print("ignored")
        self.assertIs(sys.stdout, self._original_stdout)
        self.assertIs(sys.stderr, self._original_stderr)


if __name__ == "__main__":
    unittest.main()
