from pathlib import Path
from subprocess import run


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    # Fix: Use argument lists instead of shell=True to prevent command injection
    run(
        [
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

    pip_args = ["pip", "--disable-pip-version-check", "install", "--no-deps", "-U"]
    for pkg in packages:
        pip_args.extend(["-e", pkg])

    run(pip_args).check_returncode()


if __name__ == "__main__":
    main()
