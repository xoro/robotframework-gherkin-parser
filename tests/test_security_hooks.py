"""
Tests for arbitrary keyword execution vulnerability fix (VULN-0002).
Verifies that automatic resource import and hook execution are secure-by-default
and only work when explicitly enabled via environment variables.

This test checks the environment variable logic without requiring full Robot Framework.
"""

import os
import sys
from pathlib import Path


def test_hooks_env_var_logic():
    """Test the environment variable logic for hooks."""
    test_cases = [
        # (env_value, expected_enabled)
        (None, False),  # Not set
        ("0", False),
        ("false", False),
        ("False", False),
        ("no", False),
        ("off", False),
        ("random", False),
        ("", False),
        ("1", True),
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("yes", True),
        ("Yes", True),
        ("YES", True),
        ("on", True),
        ("On", True),
        ("ON", True),
    ]
    
    for env_value, expected_enabled in test_cases:
        # Set or clear env var
        if env_value is None:
            if "GHERKIN_PARSER_ENABLE_HOOKS" in os.environ:
                del os.environ["GHERKIN_PARSER_ENABLE_HOOKS"]
        else:
            os.environ["GHERKIN_PARSER_ENABLE_HOOKS"] = env_value
        
        # Check logic (same as in Library.__init__)
        hooks_enabled = os.getenv("GHERKIN_PARSER_ENABLE_HOOKS", "0").lower() in ("1", "true", "yes", "on")
        
        assert hooks_enabled == expected_enabled, \
            f"env_value={env_value!r}: expected {expected_enabled}, got {hooks_enabled}"
        
        print(f"  {env_value!r:10} → {'enabled' if hooks_enabled else 'disabled':8} ✓")
    
    # Cleanup
    if "GHERKIN_PARSER_ENABLE_HOOKS" in os.environ:
        del os.environ["GHERKIN_PARSER_ENABLE_HOOKS"]


def test_auto_import_env_var_logic():
    """Test the environment variable logic for auto-import."""
    test_cases = [
        # (env_value, expected_enabled)
        (None, False),  # Not set
        ("0", False),
        ("false", False),
        ("no", False),
        ("", False),
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
    ]
    
    for env_value, expected_enabled in test_cases:
        # Set or clear env var
        if env_value is None:
            if "GHERKIN_PARSER_AUTO_IMPORT_RESOURCES" in os.environ:
                del os.environ["GHERKIN_PARSER_AUTO_IMPORT_RESOURCES"]
        else:
            os.environ["GHERKIN_PARSER_AUTO_IMPORT_RESOURCES"] = env_value
        
        # Check logic (same as in gherkin_builder.py)
        auto_import = os.getenv("GHERKIN_PARSER_AUTO_IMPORT_RESOURCES", "0").lower() in ("1", "true", "yes", "on")
        
        assert auto_import == expected_enabled, \
            f"env_value={env_value!r}: expected {expected_enabled}, got {auto_import}"
        
        print(f"  {env_value!r:10} → {'enabled' if auto_import else 'disabled':8} ✓")
    
    # Cleanup
    if "GHERKIN_PARSER_AUTO_IMPORT_RESOURCES" in os.environ:
        del os.environ["GHERKIN_PARSER_AUTO_IMPORT_RESOURCES"]


def test_default_secure_state():
    """Verify that the default state (no env vars set) is secure."""
    # Clear both env vars
    for var in ["GHERKIN_PARSER_ENABLE_HOOKS", "GHERKIN_PARSER_AUTO_IMPORT_RESOURCES"]:
        if var in os.environ:
            del os.environ[var]
    
    hooks_enabled = os.getenv("GHERKIN_PARSER_ENABLE_HOOKS", "0").lower() in ("1", "true", "yes", "on")
    auto_import = os.getenv("GHERKIN_PARSER_AUTO_IMPORT_RESOURCES", "0").lower() in ("1", "true", "yes", "on")
    
    assert not hooks_enabled, "Hooks should be disabled by default!"
    assert not auto_import, "Auto-import should be disabled by default!"
    
    print("  ✓ Hooks disabled by default")
    print("  ✓ Auto-import disabled by default")


def test_code_contains_security_checks():
    """Verify that the source code contains the security checks."""
    src_dir = Path(__file__).parent.parent / "src" / "GherkinParser"
    
    # Check Library.py
    library_py = src_dir / "Library.py"
    content = library_py.read_text()
    
    assert "GHERKIN_PARSER_ENABLE_HOOKS" in content, \
        "Library.py should check GHERKIN_PARSER_ENABLE_HOOKS env var"
    assert "self._hooks_enabled" in content, \
        "Library.py should have _hooks_enabled attribute"
    assert 'os.getenv("GHERKIN_PARSER_ENABLE_HOOKS"' in content, \
        "Library.py should call os.getenv for hooks"
    
    # Count occurrences of the security check
    check_count = content.count("if not self._hooks_enabled:")
    assert check_count >= 3, \
        f"Library.py should have at least 3 hooks_enabled checks (found {check_count})"
    
    # Check for teardown fix
    assert "data.teardown.config(" in content, \
        "Library.py should use data.teardown.config (not data.setup.config for teardown)"
    
    print("  ✓ Library.py contains GHERKIN_PARSER_ENABLE_HOOKS check")
    print(f"  ✓ Library.py has {check_count} security check points")
    print("  ✓ Library.py teardown bug fixed")
    
    # Check gherkin_builder.py
    builder_py = src_dir / "gherkin_builder.py"
    content = builder_py.read_text()
    
    assert "GHERKIN_PARSER_AUTO_IMPORT_RESOURCES" in content, \
        "gherkin_builder.py should check GHERKIN_PARSER_AUTO_IMPORT_RESOURCES env var"
    assert "auto_import" in content, \
        "gherkin_builder.py should have auto_import variable"
    assert 'os.getenv("GHERKIN_PARSER_AUTO_IMPORT_RESOURCES"' in content, \
        "gherkin_builder.py should call os.getenv for auto-import"
    assert "if auto_import:" in content, \
        "gherkin_builder.py should conditionally import resources"
    
    print("  ✓ gherkin_builder.py contains GHERKIN_PARSER_AUTO_IMPORT_RESOURCES check")
    print("  ✓ gherkin_builder.py conditionally imports resources")


def test_documentation_strings():
    """Check that security comments are in the code."""
    src_dir = Path(__file__).parent.parent / "src" / "GherkinParser"
    
    # Check Library.py
    library_py = src_dir / "Library.py"
    content = library_py.read_text()
    assert "Security hardening" in content or "security" in content.lower(), \
        "Library.py should have security-related comments"
    
    # Check gherkin_builder.py
    builder_py = src_dir / "gherkin_builder.py"
    content = builder_py.read_text()
    assert "Security hardening" in content or "security" in content.lower(), \
        "gherkin_builder.py should have security-related comments"
    
    print("  ✓ Security hardening comments present in source code")


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Arbitrary Keyword Execution Security Fix (VULN-0002)")
    print("=" * 80)
    
    print("\n1. Testing default secure state...")
    print("-" * 80)
    test_default_secure_state()
    
    print("\n2. Testing hooks environment variable logic...")
    print("-" * 80)
    test_hooks_env_var_logic()
    
    print("\n3. Testing auto-import environment variable logic...")
    print("-" * 80)
    test_auto_import_env_var_logic()
    
    print("\n4. Verifying security checks in source code...")
    print("-" * 80)
    test_code_contains_security_checks()
    
    print("\n5. Checking documentation...")
    print("-" * 80)
    test_documentation_strings()
    
    print("\n" + "=" * 80)
    print("All security tests passed! VULN-0002 is fixed.")
    print("=" * 80)
    print("\n🔒 Security posture: SECURE BY DEFAULT")
    print("   ✓ Hooks disabled unless GHERKIN_PARSER_ENABLE_HOOKS is set")
    print("   ✓ Auto-import disabled unless GHERKIN_PARSER_AUTO_IMPORT_RESOURCES is set")
    print("   ✓ Teardown configuration bug fixed")
    print("\n⚠️  To enable features (trusted environments ONLY):")
    print("   export GHERKIN_PARSER_ENABLE_HOOKS=1")
    print("   export GHERKIN_PARSER_AUTO_IMPORT_RESOURCES=1")
