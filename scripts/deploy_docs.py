import contextlib
import sys
from pathlib import Path
from subprocess import run

if __name__ == "__main__" and __package__ is None or __package__ == "":
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from scripts.tools import get_current_version_from_git


def main() -> None:
    version = get_current_version_from_git()
    alias = "latest"

    if version.prerelease:
        version = version.next_minor()
        alias = "dev"

    version.major, version.minor

    # Fix PATH hijack: Use sys.executable -m mike to avoid PATH resolution
    run(
        [
            sys.executable,
            "-m",
            "mike",
            "deploy",
            "--push",
            "--update-aliases",
            "--rebase",
            "--force",
            "--title",
            f"v{version.major}.{version.minor}.x ({alias})",
            f"{version.major}.{version.minor}",
            alias,
        ]
    ).check_returncode()


if __name__ == "__main__":
    main()
