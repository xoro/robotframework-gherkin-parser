"""
Tests for symlink-induced DoS vulnerability fix (VULN-0001 from d900 report).
Verifies that iter_files safely handles symlink cycles and doesn't recurse infinitely.
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Direct import to avoid Robot Framework dependency
import importlib.util
spec = importlib.util.spec_from_file_location(
    "glob_path",
    Path(__file__).parent.parent / "src" / "GherkinParser" / "glob_path.py"
)
glob_path_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glob_path_module)

iter_files = glob_path_module.iter_files


def test_self_referential_symlink():
    """Test that self-referential symlinks (dir -> .) are handled safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "test_self_ref"
        base.mkdir()
        
        # Create a symlink pointing to current directory
        loop_link = base / "loop"
        os.symlink(".", loop_link)
        
        # Create a regular file to verify we still find it
        (base / "test.txt").write_text("test")
        
        # Test 1: Default behavior (follow_symlinks=False) should skip symlinks
        start = time.perf_counter()
        results = list(iter_files(base, patterns=None, follow_symlinks=False))
        elapsed = time.perf_counter() - start
        
        assert len(results) == 1, f"Expected 1 file (test.txt), got {len(results)}"
        assert elapsed < 1.0, f"Took too long: {elapsed:.4f}s"
        print(f"✓ Self-referential symlink skipped (follow_symlinks=False): {len(results)} files in {elapsed:.4f}s")
        
        # Test 2: With follow_symlinks=True, cycle detection should prevent infinite loop
        start2 = time.perf_counter()
        results2 = list(iter_files(base, patterns=None, follow_symlinks=True))
        elapsed2 = time.perf_counter() - start2
        
        assert len(results2) >= 1, f"Should find at least test.txt"
        assert elapsed2 < 1.0, f"Cycle detection failed, took: {elapsed2:.4f}s"
        print(f"✓ Self-referential symlink with cycle detection (follow_symlinks=True): {len(results2)} files in {elapsed2:.4f}s")


def test_cross_directory_symlink_cycle():
    """Test that cross-directory symlink cycles are handled safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "test_cross_cycle"
        base.mkdir()
        
        dir_a = base / "dir_a"
        dir_b = base / "dir_b"
        dir_a.mkdir()
        dir_b.mkdir()
        
        # Create cycle: dir_a/link_to_b -> ../dir_b, dir_b/link_to_a -> ../dir_a
        (dir_a / "link_to_b").symlink_to("../dir_b")
        (dir_b / "link_to_a").symlink_to("../dir_a")
        
        # Add files in both directories
        (dir_a / "file_a.txt").write_text("a")
        (dir_b / "file_b.txt").write_text("b")
        
        # Test 1: Default (skip symlinks)
        start = time.perf_counter()
        results = list(iter_files(base, patterns=None, follow_symlinks=False))
        elapsed = time.perf_counter() - start
        
        assert len(results) == 2, f"Expected 2 files, got {len(results)}"
        assert elapsed < 1.0, f"Took too long: {elapsed:.4f}s"
        print(f"✓ Cross-directory cycle skipped (follow_symlinks=False): {len(results)} files in {elapsed:.4f}s")
        
        # Test 2: With follow_symlinks=True and cycle detection
        start2 = time.perf_counter()
        results2 = list(iter_files(base, patterns=None, follow_symlinks=True))
        elapsed2 = time.perf_counter() - start2
        
        assert len(results2) >= 2, f"Should find at least 2 files"
        assert elapsed2 < 1.0, f"Cycle detection took too long: {elapsed2:.4f}s"
        print(f"✓ Cross-directory cycle with detection (follow_symlinks=True): {len(results2)} files in {elapsed2:.4f}s")


def test_max_depth_limiting():
    """Test that max_depth parameter limits recursion depth."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "test_depth"
        base.mkdir()
        
        # Create deep directory hierarchy
        current = base
        for i in range(10):
            current = current / f"level_{i}"
            current.mkdir()
            (current / f"file_{i}.txt").write_text(f"level {i}")
        
        # Test unlimited depth
        results_unlimited = list(iter_files(base, patterns=None, follow_symlinks=False))
        files_unlimited = len(results_unlimited)
        
        # Test with max_depth=3 (should stop at level 2, since root is depth 0)
        results_limited = list(iter_files(base, patterns=None, max_depth=3))
        files_limited = len(results_limited)
        
        assert files_limited < files_unlimited, \
            f"max_depth should limit files: limited={files_limited}, unlimited={files_unlimited}"
        print(f"✓ max_depth limiting works: unlimited={files_unlimited}, max_depth=3 gives {files_limited}")


def test_symlink_to_file():
    """Verify that symlinks to files are still followed (not directories)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "test_file_symlink"
        base.mkdir()
        
        # Create a file and a symlink to it
        real_file = base / "real.txt"
        real_file.write_text("content")
        
        symlink_file = base / "link.txt"
        symlink_file.symlink_to(real_file)
        
        # Both should be found (file symlinks are not directories)
        results = list(iter_files(base, patterns=None, follow_symlinks=False))
        
        # We expect to find both the real file and the symlinked file
        assert len(results) == 2, f"Expected 2 files, got {len(results)}"
        print(f"✓ File symlinks are traversed: {len(results)} files found")


def test_pattern_matching_with_symlinks():
    """Test that pattern matching works correctly with symlink skipping."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "test_patterns"
        base.mkdir()
        
        # Create structure
        (base / "test.feature").write_text("feature")
        (base / "test.resource").write_text("resource")
        
        subdir = base / "subdir"
        subdir.mkdir()
        (subdir / "nested.feature").write_text("nested feature")
        
        # Create symlink loop
        (subdir / "loop").symlink_to("..")
        
        # Search for *.feature files
        results = list(iter_files(base, patterns="**/*.feature", follow_symlinks=False))
        
        assert len(results) == 2, f"Expected 2 .feature files, got {len(results)}"
        print(f"✓ Pattern matching with symlink skipping: {len(results)} .feature files")


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Symlink DoS Vulnerability Fix")
    print("=" * 80)
    
    print("\n1. Testing self-referential symlinks...")
    print("-" * 80)
    test_self_referential_symlink()
    
    print("\n2. Testing cross-directory symlink cycles...")
    print("-" * 80)
    test_cross_directory_symlink_cycle()
    
    print("\n3. Testing max_depth limiting...")
    print("-" * 80)
    test_max_depth_limiting()
    
    print("\n4. Testing file symlinks (should work)...")
    print("-" * 80)
    test_symlink_to_file()
    
    print("\n5. Testing pattern matching with symlinks...")
    print("-" * 80)
    test_pattern_matching_with_symlinks()
    
    print("\n" + "=" * 80)
    print("All tests passed! Symlink DoS vulnerability is fixed.")
    print("=" * 80)
    print("\n🔒 Security improvements:")
    print("   ✓ Symlinked directories skipped by default (follow_symlinks=False)")
    print("   ✓ Cycle detection via visited set prevents infinite loops")
    print("   ✓ Optional max_depth parameter for additional safety")
    print("   ✓ File symlinks still work normally")
