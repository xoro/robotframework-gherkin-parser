"""
Test suite for reentrancy guard protection in Library.call_hooks()

Validates fix for VULN-0001 (a4a1): Denial of Service (DoS) via broken reentrancy guard.
This test ensures that when a hook keyword attempts to call back into hook processing,
the reentrancy guard prevents infinite recursion.

CVSS: 5.5 (MEDIUM)
Impact: Prevents unbounded recursion leading to CPU exhaustion and test runner failure
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import importlib.util

# Dynamically import the Library module without Robot Framework
repo_root = Path(__file__).parent.parent

# Mock Robot Framework modules BEFORE importing Library
sys.modules['robot'] = MagicMock()
sys.modules['robot.result'] = MagicMock()
sys.modules['robot.running'] = MagicMock()
sys.modules['robot.running.builder'] = MagicMock()
sys.modules['robot.running.builder.settings'] = MagicMock()
sys.modules['robot.running.builder.transformers'] = MagicMock()
sys.modules['robot.api'] = MagicMock()
sys.modules['robot.api.deco'] = MagicMock()
sys.modules['robot.api.interfaces'] = MagicMock()
sys.modules['robot.libraries'] = MagicMock()
sys.modules['robot.libraries.BuiltIn'] = MagicMock()

# Mock the library decorator to pass through
def mock_library(*args, **kwargs):
    def decorator(cls):
        return cls
    return decorator
sys.modules['robot.api.deco'].library = mock_library

# Mock ListenerV3 as a class
class MockListenerV3:
    pass
sys.modules['robot.api.interfaces'].ListenerV3 = MockListenerV3

# Create mock BuiltIn with EXECUTION_CONTEXTS
mock_builtin_module = MagicMock()
mock_builtin_module.EXECUTION_CONTEXTS = MagicMock()
mock_builtin_module.BuiltIn = MagicMock
sys.modules['robot.libraries.BuiltIn'] = mock_builtin_module

# Import Library.py directly without going through package __init__.py
library_path = repo_root / "src" / "GherkinParser" / "Library.py"
spec = importlib.util.spec_from_file_location("GherkinParser.Library", library_path)
library_module = importlib.util.module_from_spec(spec)
sys.modules['GherkinParser.Library'] = library_module
spec.loader.exec_module(library_module)

Library = library_module.Library


class TestReentrancyGuard(unittest.TestCase):
    """Test that the reentrancy guard in call_hooks() prevents infinite recursion"""

    def setUp(self):
        """Set up test fixtures and mock Robot Framework dependencies"""
        # Create a mock keyword with hook tag
        self.mock_keyword = Mock()
        self.mock_keyword.name = "Before Test Hook"
        self.mock_keyword.tags = ["hook:before-test"]

        # Create mock resource container
        mock_resource = Mock()
        mock_resource.name = "test_resource"
        mock_resource.keywords = [self.mock_keyword]

        # Create mock keyword store
        mock_kw_store = Mock()
        mock_kw_store.resources.values.return_value = [mock_resource]
        mock_kw_store.libraries.values.return_value = []

        # Create mock namespace
        mock_namespace = Mock()
        mock_namespace._kw_store = mock_kw_store

        # Create mock runner
        mock_runner = Mock()
        mock_runner.keyword = self.mock_keyword

        # Create mock context
        mock_context = Mock()
        mock_context.namespace = mock_namespace
        mock_context.get_runner.return_value = mock_runner

        # Patch EXECUTION_CONTEXTS in the Library module
        self.exec_contexts_patcher = patch.object(library_module, 'EXECUTION_CONTEXTS')
        mock_exec_contexts = self.exec_contexts_patcher.start()
        mock_exec_contexts.current = mock_context

        # Create mock BuiltIn
        self.builtin_patcher = patch.object(library_module, 'BuiltIn')
        mock_builtin_class = self.builtin_patcher.start()
        self.builtin_mock = MagicMock()
        mock_builtin_class.return_value = self.builtin_mock

        self.reentry_count = 0
        self.max_reentries = 5

        # Set up run_keyword to attempt re-entry
        def reenter_on_call(*args, **kwargs):
            self.reentry_count += 1
            if self.reentry_count <= self.max_reentries:
                # Attempt to re-enter call_hooks
                # If guard works, this should be blocked
                self.library_instance.call_hooks("before-test")

        self.builtin_mock.run_keyword.side_effect = reenter_on_call

    def tearDown(self):
        """Clean up patches"""
        self.exec_contexts_patcher.stop()
        self.builtin_patcher.stop()

    def test_reentrancy_guard_prevents_infinite_recursion(self):
        """Verify that the reentrancy guard prevents hooks from recursively calling themselves"""
        # Create library instance with hooks enabled
        self.library_instance = Library()
        self.library_instance._hooks_enabled = True

        # Trigger initial call_hooks
        self.library_instance.call_hooks("before-test")

        # Assert that run_keyword was called exactly once
        # Without the guard, it would be called multiple times (up to max_reentries)
        self.assertEqual(self.builtin_mock.run_keyword.call_count, 1,
                         "Hook should be executed exactly once; reentrancy should be blocked")

        # Verify reentry attempts were made but blocked
        self.assertEqual(self.reentry_count, 1,
                         "Reentrancy guard should prevent additional hook executions")

    def test_reentrancy_guard_resets_after_completion(self):
        """Verify that the reentrancy guard is properly reset after call_hooks completes"""
        # Create library instance with hooks enabled
        self.library_instance = Library()
        self.library_instance._hooks_enabled = True

        # Configure run_keyword to NOT attempt re-entry on first call
        self.builtin_mock.run_keyword.side_effect = None

        # First call should succeed
        self.library_instance.call_hooks("before-test")
        self.assertEqual(self.builtin_mock.run_keyword.call_count, 1)

        # Verify guard is reset to False
        self.assertFalse(self.library_instance._in_call_hooks,
                        "Reentrancy guard should be reset to False after completion")

        # Second call should also succeed (guard was properly reset)
        self.builtin_mock.run_keyword.reset_mock()
        self.library_instance.call_hooks("before-test")
        self.assertEqual(self.builtin_mock.run_keyword.call_count, 1)

    def test_reentrancy_guard_resets_on_exception(self):
        """Verify that the reentrancy guard is reset even when an exception occurs"""
        # Create library instance with hooks enabled
        self.library_instance = Library()
        self.library_instance._hooks_enabled = True

        # Configure run_keyword to raise an exception
        test_exception = ValueError("Test exception in hook")
        self.builtin_mock.run_keyword.side_effect = test_exception

        # Call may or may not propagate exception depending on error handling
        # What matters is that the guard is reset
        try:
            self.library_instance.call_hooks("before-test")
        except ValueError:
            pass  # Exception may be raised, which is fine

        # Verify guard is reset to False even after exception
        self.assertFalse(self.library_instance._in_call_hooks,
                        "Reentrancy guard should be reset to False even after exception")

        # Verify another call can proceed (guard was properly reset)
        self.builtin_mock.run_keyword.side_effect = None
        self.builtin_mock.run_keyword.reset_mock()
        self.library_instance.call_hooks("before-test")
        self.assertEqual(self.builtin_mock.run_keyword.call_count, 1)

    def test_no_execution_when_already_in_call_hooks(self):
        """Verify that call_hooks returns immediately when reentrancy guard is active"""
        # Create library instance with hooks enabled
        self.library_instance = Library()
        self.library_instance._hooks_enabled = True

        # Manually set guard to True (simulating we're already inside call_hooks)
        self.library_instance._in_call_hooks = True

        # Call should return immediately without executing any hooks
        self.library_instance.call_hooks("before-test")

        # Verify no keywords were executed
        self.assertEqual(self.builtin_mock.run_keyword.call_count, 0,
                        "No hooks should execute when reentrancy guard is active")

    def test_guard_inactive_when_hooks_disabled(self):
        """Verify that when hooks are disabled, the guard logic is not relevant"""
        # Create library instance with hooks DISABLED (default)
        self.library_instance = Library()
        self.library_instance._hooks_enabled = False

        # Call should return immediately
        self.library_instance.call_hooks("before-test")

        # Verify no keywords were executed
        self.assertEqual(self.builtin_mock.run_keyword.call_count, 0)

        # Verify guard remains False
        self.assertFalse(self.library_instance._in_call_hooks)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
