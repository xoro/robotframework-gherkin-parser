"""
Tests for ReDoS vulnerability fix in glob_path module.
Verifies that the globstar ("**") translation no longer creates nested quantifier patterns
that cause catastrophic backtracking.
"""

import re
import time
import multiprocessing as mp
from pathlib import Path
import sys
import os

# Add src to path and directly import just the function we need
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Direct import of the function to test, avoiding full module dependencies
import importlib.util

spec = importlib.util.spec_from_file_location(
    "glob_path", Path(__file__).parent.parent / "src" / "GherkinParser" / "glob_path.py"
)
glob_path_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glob_path_module)

_glob_pattern_to_re = glob_path_module._glob_pattern_to_re


def globmatches(pattern: str, path_str: str) -> bool:
    """Simple glob matching for testing."""
    regex = _glob_pattern_to_re(pattern)
    compiled = re.compile(regex)
    normalized_path = str(path_str).replace(os.sep, "/")
    return compiled.fullmatch(normalized_path) is not None


def test_no_nested_quantifiers():
    """Verify that generated regex patterns don't contain nested quantifiers."""
    test_cases = [
        "**/*a",
        "**/*.resource",
        "/**/**/**/a",
        "**/test/**/*.py",
    ]

    for pattern in test_cases:
        regex = _glob_pattern_to_re(pattern)
        print(f"Pattern: {pattern}")
        print(f"Regex:   {regex}\n")

        # Check that we don't have the vulnerable nested pattern ((?:[^/]*(?:/|$))*)
        assert "((?:[^/]*(?:/|$))*)" not in regex, f"Pattern {pattern} still contains nested quantifier!"

        # The fixed pattern should use (?:[^/]+/)* or .* instead
        assert "(?:[^/]+/)*" in regex or ".*" in regex, f"Pattern {pattern} doesn't use the fixed pattern!"


def _match_worker(q, pattern, path_str):
    """Worker process for timing regex match with timeout."""
    try:
        import re
        import os
        import importlib.util
        from pathlib import Path

        # Load the module in worker process
        spec = importlib.util.spec_from_file_location(
            "glob_path", Path(__file__).parent.parent / "src" / "GherkinParser" / "glob_path.py"
        )
        glob_path_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(glob_path_module)

        regex = glob_path_module._glob_pattern_to_re(pattern)
        compiled = re.compile(regex)
        normalized_path = str(path_str).replace(os.sep, "/")
        result = compiled.fullmatch(normalized_path) is not None

        q.put({"matched": result, "error": None})
    except Exception as e:
        q.put({"matched": False, "error": str(e)})


def timed_globmatch(pattern: str, path_str: str, timeout_sec: float = 2.0):
    """
    Test glob matching with timeout to detect catastrophic backtracking.
    Returns (matched, elapsed_time, status).
    """
    q = mp.Queue()
    p = mp.Process(target=_match_worker, args=(q, pattern, path_str))
    start = time.perf_counter()
    p.start()
    p.join(timeout=timeout_sec)

    if p.is_alive():
        p.terminate()
        p.join()
        elapsed = time.perf_counter() - start
        return (False, elapsed, "timeout")

    elapsed = time.perf_counter() - start
    if not q.empty():
        res = q.get()
        if res.get("error"):
            return (False, elapsed, f"error:{res['error']}")
        return (res.get("matched", False), elapsed, "ok")
    return (False, elapsed, "error:NoResult")


def test_performance_worst_case():
    """
    Test that worst-case inputs (that would trigger ReDoS in the old implementation)
    complete quickly with the fixed implementation.
    """
    test_cases = [
        # Multi-globstar with many segments ending in mismatch
        ("/**/**/**/a", "/" + ("a/" * 100) + "b"),
        # Single globstar with long segment
        ("**/*a", "a" * 1000 + "b"),
        # Resource pattern with no match
        ("**/*.resource", "a" * 1000),
        # Multiple directory levels
        ("**/test/**/*.py", "/".join(["dir"] * 50) + "/nomatch.txt"),
    ]

    timeout = 2.0  # Should complete well under 2 seconds with fix

    for pattern, path_str in test_cases:
        matched, elapsed, status = timed_globmatch(pattern, path_str, timeout_sec=timeout)
        print(f"Pattern: {pattern}")
        print(f"Path length: {len(path_str)}")
        print(f"Elapsed: {elapsed:.4f}s, Status: {status}, Matched: {matched}\n")

        assert status != "timeout", f"Pattern {pattern} timed out - ReDoS vulnerability may still exist!"

        # Should complete very quickly (well under timeout)
        assert elapsed < 0.5, f"Pattern {pattern} took {elapsed:.4f}s - too slow, potential performance issue!"


def test_basic_functionality():
    """Verify that basic glob matching still works correctly after the fix."""
    test_cases = [
        # (pattern, path, should_match)
        ("**/*.resource", "test.resource", True),
        ("**/*.resource", "path/to/test.resource", True),
        ("**/*.resource", "deep/path/to/test.resource", True),
        ("**/*.resource", "test.txt", False),
        ("**/test/**/*.py", "test/file.py", True),
        ("**/test/**/*.py", "src/test/file.py", True),
        ("**/test/**/*.py", "src/test/nested/file.py", True),
        ("**/test/**/*.py", "src/other/file.py", False),
        ("**/*", "any/path/file.txt", True),
        ("**/*", "file.txt", True),
        ("*.feature", "test.feature", True),
        ("*.feature", "path/test.feature", False),
        ("**/*.feature", "test.feature", True),
        ("**/*.feature", "features/test.feature", True),
        ("**/*.feature", "deep/features/test.feature", True),
    ]

    for pattern, path, should_match in test_cases:
        result = globmatches(pattern, path)
        print(
            f"Pattern: {pattern:30} Path: {path:35} Expected: {should_match:5} Got: {result:5} {'✓' if result == should_match else '✗'}"
        )
        assert (
            result == should_match
        ), f"Pattern {pattern} {'should' if should_match else 'should not'} match {path}, but got {result}"


if __name__ == "__main__":
    print("=" * 80)
    print("Testing ReDoS Fix in glob_path module")
    print("=" * 80)

    print("\n1. Testing for nested quantifiers...")
    print("-" * 80)
    test_no_nested_quantifiers()
    print("✓ No nested quantifiers found!\n")

    print("\n2. Testing performance with worst-case inputs...")
    print("-" * 80)
    test_performance_worst_case()
    print("✓ Performance is acceptable!\n")

    print("\n3. Testing basic functionality...")
    print("-" * 80)
    test_basic_functionality()
    print("✓ Basic functionality works correctly!\n")

    print("=" * 80)
    print("All tests passed! ReDoS vulnerability is fixed.")
    print("=" * 80)
