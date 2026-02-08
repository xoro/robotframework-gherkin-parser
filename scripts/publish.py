import contextlib
import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Any, Sequence

if __name__ == "__main__" and __package__ is None or __package__ == "":
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from scripts.tools import get_version


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
    dist_path = Path("./dist").absolute()

    if not dist_path.exists():
        raise FileNotFoundError(f"dist folder '{dist_path}' not exists")

    current_version = get_version()

    vsix_path = Path(dist_path, f"robotcode-gherkin-{current_version}.vsix")

    # Fix PATH hijack: Resolve npx to absolute path to avoid PATH resolution
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx not found in PATH")

    run("npx vsce publish", [npx, "vsce", "publish", "-i", str(vsix_path)], timeout=600)
    run("npx ovsx publish", [npx, "ovsx", "publish", str(vsix_path)], timeout=600)

    # Fix PATH hijack: Use sys.executable -m hatch to avoid PATH resolution
    hatch_args = [sys.executable, "-m", "hatch", "-e", "build", "publish"]
    if os.environ.get("PYPI_USERNAME") and os.environ.get("PYPI_PASSWORD"):
        hatch_args += ["-u", os.environ["PYPI_USERNAME"], "-a", os.environ["PYPI_PASSWORD"]]

    run("hatch publish", hatch_args, timeout=600)


if __name__ == "__main__":
    main()
