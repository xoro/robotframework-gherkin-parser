import contextlib
import shutil
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


from scripts.tools import get_version

PRE_RELEASE = True


def main() -> None:
    dist_path = Path("./dist").absolute()
    if not dist_path.exists():
        dist_path.mkdir()

    # Fix PATH hijack: Use sys.executable -m hatch to avoid PATH resolution
    packages = [f"{path}" for path in Path("./packages").iterdir() if (path / "pyproject.toml").exists()]
    for package in packages:
        run([sys.executable, "-m", "hatch", "-e", "build", "build", str(dist_path)], cwd=package).check_returncode()

    run([sys.executable, "-m", "hatch", "-e", "build", "build", str(dist_path)]).check_returncode()

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
    pip_args.extend(packages)
    pip_args.append(".")
    run(pip_args).check_returncode()

    # Fix PATH hijack: Resolve npx to absolute path to avoid PATH resolution
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx not found in PATH")

    vsce_args = [npx, "vsce", "package"]
    if PRE_RELEASE or get_version().prerelease:
        vsce_args.append("--pre-release")
    vsce_args.extend(["-o", "./dist"])
    run(vsce_args).check_returncode()


if __name__ == "__main__":
    main()
