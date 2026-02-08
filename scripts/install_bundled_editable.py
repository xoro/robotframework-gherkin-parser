import shutil
import sys
from pathlib import Path
from subprocess import run


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    shutil.rmtree("./bundled/libs", ignore_errors=True)

    # Fix PATH hijack: Use sys.executable -m pip to avoid PATH resolution
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            "-U",
            "-t",
            "./bundled/libs",
            "--no-cache-dir",
            "--implementation",
            "py",
            "--only-binary=:all:",
            "--no-binary=:none:",
            "-r",
            "./bundled_requirements.txt",
        ]
    ).check_returncode()

    packages = [f"{path}" for path in Path("./packages").iterdir() if (path / "pyproject.toml").exists()]

    # Build command with package paths as separate arguments
    pip_args = [
        sys.executable,
        "-m",
        "pip",
        "--disable-pip-version-check",
        "install",
        "-U",
        "-t",
        "./bundled/libs",
        "--no-cache-dir",
        "--implementation",
        "py",
        "--no-deps",
    ]
    for pkg in packages:
        pip_args.extend(["-e", pkg])
    pip_args.extend(["-e", "."])

    run(pip_args).check_returncode()


if __name__ == "__main__":
    main()
