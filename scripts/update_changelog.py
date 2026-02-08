import contextlib
import subprocess
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from scripts.tools import get_version
from typing import Sequence


def run(title: str, args: Sequence[str], **kwargs: Any) -> None:
    """Execute a command safely without shell interpretation.
    
    Args:
        title: Description of the command for logging
        args: Command and arguments as a list/sequence
        **kwargs: Additional arguments to pass to subprocess.run
    """
    try:
        print(f"running {title}")
        kwargs.setdefault("check", True)
        subprocess.run(args, **kwargs)
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException as e:
        print(f"{title} failed: {e}", file=sys.stderr)


def main() -> None:
    current_version = get_version()

    # Fix: Use argument list instead of shell=True to prevent command injection
    run(
        "create changelog",
        ["git-cliff", "--bump", "-t", f"v{current_version}", "-o", "CHANGELOG.md"],
        timeout=600,
    )


if __name__ == "__main__":
    main()
