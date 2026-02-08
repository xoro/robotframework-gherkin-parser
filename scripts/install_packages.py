from pathlib import Path
from subprocess import run
import sys


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    # Fix PATH hijack: Use sys.executable -m pip to avoid PATH resolution
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            "-U",
            "-r",
            "./bundled_requirements.txt",
        ]
    ).check_returncode()

    packages = [f"{path}" for path in Path("./packages").iterdir() if (path / "pyproject.toml").exists()]

    if not packages:
        return

    pip_args = [sys.executable, "-m", "pip", "--disable-pip-version-check", "install", "--no-deps", "-U"]
    for pkg in packages:
        pip_args.extend(["-e", pkg])

    run(pip_args).check_returncode()


if __name__ == "__main__":
    main()
