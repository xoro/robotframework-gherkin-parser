"""
Tests for vulnerabilities vuln-0001 (symlink traversal) and vuln-0002 (? wildcard)
from the bea6 Strix security scan.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "glob_path", Path(__file__).parent.parent / "src" / "GherkinParser" / "glob_path.py"
)
glob_path_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glob_path_module)

iter_files = glob_path_module.iter_files
globmatches = glob_path_module.globmatches
_glob_pattern_to_re = glob_path_module._glob_pattern_to_re


# ---- vuln-0002: ? wildcard must not match directory separator ----


def test_question_mark_does_not_match_slash():
    """The ? glob wildcard should match any single character except '/'."""
    assert globmatches("a?b", "axb") is True
    assert globmatches("a?b", "a/b") is False  # was True before fix
    assert globmatches("src?.py", "srcx.py") is True
    assert globmatches("src?.py", "src/.py") is False  # was True before fix


def test_question_mark_regex_excludes_separator():
    """Verify the regex produced for ? uses [^/] instead of '.'."""
    regex = _glob_pattern_to_re("a?b")
    assert "[^/]" in regex, f"Expected [^/] in regex, got: {regex}"
    assert regex.count(".") == 0 or "(?ms)" in regex  # only the flag prefix dot


def test_question_mark_in_pattern_with_iter_files():
    """iter_files with a ? pattern must not cross directory boundaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "project"
        base.mkdir()

        # File that should match a?b.txt
        (base / "axb.txt").write_text("match")

        # File in subdir that would incorrectly match if ? matches /
        sub = base / "a"
        sub.mkdir()
        (sub / "b.txt").write_text("no match")

        results = list(iter_files(base, patterns="a?b.txt"))
        names = [r.name for r in results]

        assert "axb.txt" in names, "Should match axb.txt"
        assert "b.txt" not in names, "Should NOT match a/b.txt via ? crossing directory boundary"


# ---- vuln-0001: file symlink traversal outside scan root ----


def test_file_symlink_outside_root_is_rejected():
    """File symlinks resolving outside the scan root must be skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        project.mkdir()
        (project / "legit.resource").write_text("*** Keywords ***\nOK\n    Log    ok\n")

        # Attacker-controlled file outside project
        attacker = Path(tmpdir) / "attacker"
        attacker.mkdir()
        malicious = attacker / "evil.resource"
        malicious.write_text("*** Keywords ***\nEvil\n    Log    pwned\n")

        # Symlink inside project pointing outside
        lib = project / "lib"
        lib.mkdir()
        (lib / "helper.resource").symlink_to(malicious)

        results = list(iter_files(project, "**/*.resource"))
        resolved_paths = [r.resolve() for r in results]

        # The legitimate file should be found
        assert any("legit.resource" in str(p) for p in resolved_paths), "Should find legit.resource"

        # The symlinked file pointing outside should NOT be found
        assert not any("evil.resource" in str(p) for p in resolved_paths), (
            "File symlink pointing outside scan root should be rejected"
        )


def test_file_symlink_inside_root_is_allowed():
    """File symlinks that resolve within the scan root should still be followed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        project.mkdir()

        real = project / "real.txt"
        real.write_text("content")

        link = project / "link.txt"
        link.symlink_to(real)

        results = list(iter_files(project, follow_symlinks=False))
        assert len(results) == 2, f"Expected 2 files (real + internal symlink), got {len(results)}"


def test_file_symlink_outside_root_with_follow_symlinks():
    """When follow_symlinks=True, file symlinks outside root are still allowed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        project.mkdir()

        external = Path(tmpdir) / "external"
        external.mkdir()
        ext_file = external / "ext.txt"
        ext_file.write_text("external")

        (project / "link.txt").symlink_to(ext_file)

        # With follow_symlinks=True, the boundary check is skipped
        results = list(iter_files(project, follow_symlinks=True))
        assert len(results) == 1, f"Expected 1 file with follow_symlinks=True, got {len(results)}"
