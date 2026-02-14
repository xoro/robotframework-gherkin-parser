from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Generator, Iterable, Optional, Sequence, Set, Tuple, Union, cast


def _glob_pattern_to_re(pattern: str) -> str:
    """
    Convert a glob pattern to a regular expression with safeguards against catastrophic backtracking.
    In particular, avoid nested-quantifier expansions for the globstar ("**").
    """
    result = "(?ms)^"

    in_group = False
    i = 0
    L = len(pattern)

    while i < L:
        c = pattern[i]

        if c in "\\/$^+.()=!|":
            result += "\\" + c
        elif c == "?":
            result += "[^/]"
        elif c in "[]":
            result += c
        elif c == "{":
            in_group = True
            result += "("
        elif c == "}":
            in_group = False
            result += ")"
        elif c == ",":
            if in_group:
                result += "|"
            else:
                # literal comma
                result += "\\,"
        elif c == "*":
            prev_char = pattern[i - 1] if i > 0 else None
            star_count = 1

            # Count consecutive stars
            while (i + 1) < L and pattern[i + 1] == "*":
                star_count += 1
                i += 1

            next_char = pattern[i + 1] if (i + 1) < L else None
            is_globstar = (
                star_count > 1 and (prev_char is None or prev_char == "/") and (next_char is None or next_char == "/")
            )

            if is_globstar:
                if next_char == "/":
                    # Skip the slash in the glob pattern
                    i += 1
                    # Collapse adjacent "**/" runs into a single matcher
                    while (i + 3) < L and pattern[i] == "*" and pattern[i + 1] == "*" and pattern[i + 2] == "/":
                        i += 3
                    # Zero or more complete directory segments (non-nested)
                    result += "(?:[^/]+/)*"
                else:
                    # Trailing "**" — match any remaining characters
                    result += ".*"
            else:
                # Single "*"
                result += "([^/]*)"
        else:
            result += c

        i += 1

    result += "$"
    return result


class Pattern:
    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        self._re_pattern = re.compile(_glob_pattern_to_re(pattern))

    def matches(self, path: Union[Path, str, os.PathLike[Any]]) -> bool:
        if not isinstance(path, Path):
            path = Path(path)
        return self._re_pattern.fullmatch(str(path).replace(os.sep, "/")) is not None

    def __str__(self) -> str:
        return self.pattern

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(pattern={repr(self.pattern)}"


def globmatches(pattern: str, path: Union[Path, str, os.PathLike[Any]]) -> bool:
    return Pattern(pattern).matches(path)


def iter_files(
    path: Union[Path, str, os.PathLike[str]],
    patterns: Union[Sequence[Union[Pattern, str]], Pattern, str, None] = None,
    ignore_patterns: Union[Sequence[Union[Pattern, str]], Pattern, str, None] = None,
    *,
    absolute: bool = False,
    follow_symlinks: bool = False,
    max_depth: Optional[int] = None,
    _base_path: Union[Path, str, os.PathLike[str], None] = None,
    _depth: int = 0,
    _visited: Optional[Set[Tuple[int, int]]] = None,
) -> Generator[Path, None, None]:
    """
    Recursively iterate over files in a directory tree.

    Args:
        path: Root path to scan
        patterns: Glob patterns to match files (None = all files)
        ignore_patterns: Glob patterns to ignore
        absolute: Return absolute paths
        follow_symlinks: Follow symlinked directories (default: False for security)
        max_depth: Maximum recursion depth (None = unlimited)
        _base_path: Internal - base path for relative matching
        _depth: Internal - current recursion depth
        _visited: Internal - set of visited directory identifiers to prevent cycles
    """
    if not isinstance(path, Path):
        path = Path(path or ".")

    if _base_path is None:
        _base_path = path
    elif not isinstance(_base_path, Path):
        _base_path = Path(_base_path)

    # Initialize visited set and record current directory to prevent cycles
    if _visited is None:
        _visited = set()
    try:
        st = path.stat()
        key = (st.st_dev, st.st_ino)
        if key in _visited:
            return
        _visited.add(key)
    except OSError:
        # If we can't stat the path, skip it gracefully
        pass

    # Optional depth guard against excessively deep recursion
    if max_depth is not None and _depth >= max_depth:
        return

    if patterns is not None and isinstance(patterns, (str, Pattern)):
        patterns = [patterns]
    if patterns is not None:
        patterns = list(map(lambda p: p if isinstance(p, Pattern) else Pattern(p), patterns))

    if ignore_patterns is not None and isinstance(ignore_patterns, (str, Pattern)):
        ignore_patterns = [ignore_patterns]
    if ignore_patterns is not None:
        ignore_patterns = list(map(lambda p: p if isinstance(p, Pattern) else Pattern(p), ignore_patterns))

    try:
        # Resolve the base path once for symlink boundary checks
        resolved_base = Path(_base_path).resolve()

        for f in path.iterdir():
            # Skip symlinked directories unless explicitly allowed
            try:
                if not follow_symlinks and f.is_symlink() and f.is_dir():
                    continue
            except OSError:
                continue

            # Skip file symlinks whose targets resolve outside the scan root
            try:
                if not follow_symlinks and f.is_symlink() and f.is_file():
                    resolved_target = f.resolve()
                    if not str(resolved_target).startswith(str(resolved_base) + os.sep) and resolved_target != resolved_base:
                        continue
            except OSError:
                continue

            if ignore_patterns is None or not any(
                p.matches(f.relative_to(_base_path)) for p in cast(Iterable[Pattern], ignore_patterns)
            ):
                if f.is_dir():
                    for e in iter_files(
                        f,
                        patterns,
                        ignore_patterns,
                        absolute=absolute,
                        follow_symlinks=follow_symlinks,
                        max_depth=max_depth,
                        _base_path=_base_path,
                        _depth=_depth + 1,
                        _visited=_visited,
                    ):
                        yield e
                elif patterns is None or any(
                    p.matches(str(f.relative_to(_base_path))) for p in cast(Iterable[Pattern], patterns)
                ):
                    yield f.absolute() if absolute else f
    except (PermissionError, OSError):
        # Gracefully skip unreadable directories
        pass
