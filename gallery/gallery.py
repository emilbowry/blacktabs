import atexit
import json
import subprocess
import tarfile
import tempfile
import traceback
import venv
import zipfile
from argparse import ArgumentParser, Namespace
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache, partial
from pathlib import Path
from typing import NamedTuple, Optional, Union, cast
from urllib.request import urlopen, urlretrieve

PYPI_INSTANCE = "https://pypi.org/pypi"
PYPI_TOP_PACKAGES = (
    "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
)
INTERNAL_monochromatic_REPO = f"{tempfile.gettempdir()}/__monochromatic"

ArchiveKind = Union[tarfile.TarFile, zipfile.ZipFile]

subprocess.run = partial(subprocess.run, check=True)  # type: ignore
# https://github.com/python/mypy/issues/1484


class monochromaticVersion(NamedTuple):
    version: str
    config: Optional[str] = None


def get_pypi_download_url(package: str, version: Optional[str]) -> str:
    with urlopen(PYPI_INSTANCE + f"/{package}/json") as page:
        metadata = json.load(page)

    if version is None:
        sources = metadata["urls"]
    else:
        if version in metadata["releases"]:
            sources = metadata["releases"][version]
        else:
            raise ValueError(
                f"No releases found with version ('{version}') tag. "
                f"Found releases: {metadata['releases'].keys()}"
            )

    for source in sources:
        if source["python_version"] == "source":
            break
    else:
        raise ValueError(f"Couldn't find any sources for {package}")

    return cast(str, source["url"])


def get_top_packages() -> list[str]:
    with urlopen(PYPI_TOP_PACKAGES) as page:
        result = json.load(page)

    return [package["project"] for package in result["rows"]]


def get_package_source(package: str, version: Optional[str]) -> str:
    if package == "cpython":
        if version is None:
            version = "main"
        return f"https://github.com/python/cpython/archive/{version}.zip"
    elif package == "pypy":
        if version is None:
            version = "branch/default"
        return (
            f"https://foss.heptapod.net/pypy/pypy/repository/{version}/archive.tar.bz2"
        )
    else:
        return get_pypi_download_url(package, version)


def get_archive_manager(local_file: str) -> ArchiveKind:
    if tarfile.is_tarfile(local_file):
        return tarfile.open(local_file)
    elif zipfile.is_zipfile(local_file):
        return zipfile.ZipFile(local_file)
    else:
        raise ValueError("Unknown archive kind.")


def get_first_archive_member(archive: ArchiveKind) -> str:
    if isinstance(archive, tarfile.TarFile):
        return archive.getnames()[0]
    elif isinstance(archive, zipfile.ZipFile):
        return archive.namelist()[0]


def download_and_extract(package: str, version: Optional[str], directory: Path) -> Path:
    source = get_package_source(package, version)

    local_file, _ = urlretrieve(source, directory / f"{package}-src")
    with get_archive_manager(local_file) as archive:
        archive.extractall(path=directory)
        result_dir = get_first_archive_member(archive)
    return directory / result_dir


def get_package(
    package: str, version: Optional[str], directory: Path
) -> Optional[Path]:
    try:
        return download_and_extract(package, version, directory)
    except Exception:
        print(f"Caught an exception while downloading {package}.")
        traceback.print_exc()
        return None


DEFAULT_SLICE = slice(None)  # for flake8


def download_and_extract_top_packages(
    directory: Path,
    workers: int = 8,
    limit: slice = DEFAULT_SLICE,
) -> Generator[Path, None, None]:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        bound_downloader = partial(get_package, version=None, directory=directory)
        for package in executor.map(bound_downloader, get_top_packages()[limit]):
            if package is not None:
                yield package


def git_create_repository(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo)
    git_add_and_commit(msg="Initial commit", repo=repo)


def git_add_and_commit(msg: str, repo: Path) -> None:
    subprocess.run(["git", "add", "."], cwd=repo)
    subprocess.run(["git", "commit", "-m", msg, "--allow-empty"], cwd=repo)


def git_switch_branch(
    branch: str, repo: Path, new: bool = False, from_branch: Optional[str] = None
) -> None:
    args = ["git", "checkout"]
    if new:
        args.append("-b")
    args.append(branch)
    if from_branch:
        args.append(from_branch)
    subprocess.run(args, cwd=repo)


def init_repos(options: Namespace) -> tuple[Path, ...]:
    options.output.mkdir(exist_ok=True)

    if options.top_packages:
        source_directories = tuple(
            download_and_extract_top_packages(
                directory=options.output,
                workers=options.workers,
                limit=slice(None, options.top_packages),
            )
        )
    else:
        source_directories = (
            download_and_extract(
                package=options.pypi_package,
                version=options.version,
                directory=options.output,
            ),
        )

    for source_directory in source_directories:
        git_create_repository(source_directory)

    if options.monochromatic_repo is None:
        subprocess.run(
            ["git", "clone", "https://github.com/psf/monochromatic.git", INTERNAL_monochromatic_REPO],
            cwd=options.output,
        )
        options.monochromatic_repo = options.output / INTERNAL_monochromatic_REPO

    return source_directories


@lru_cache(8)
def monochromatic_runner(version: str, monochromatic_repo: Path) -> Path:
    directory = tempfile.TemporaryDirectory()
    venv.create(directory.name, with_pip=True)

    python = Path(directory.name) / "bin" / "python"
    subprocess.run([python, "-m", "pip", "install", "-e", monochromatic_repo])

    atexit.register(directory.cleanup)
    return python


def format_repo_with_version(
    repo: Path,
    from_branch: Optional[str],
    monochromatic_repo: Path,
    monochromatic_version: monochromaticVersion,
    input_directory: Path,
) -> str:
    current_branch = f"monochromatic-{monochromatic_version.version}"
    git_switch_branch(monochromatic_version.version, repo=monochromatic_repo)
    git_switch_branch(current_branch, repo=repo, new=True, from_branch=from_branch)

    format_cmd: list[Union[Path, str]] = [
        monochromatic_runner(monochromatic_version.version, monochromatic_repo),
        (monochromatic_repo / "monochromatic.py").resolve(),
        ".",
    ]
    if monochromatic_version.config:
        format_cmd.extend(["--config", input_directory / monochromatic_version.config])

    subprocess.run(format_cmd, cwd=repo, check=False)  # ensure the process
    # continuess to run even it can't format some files. Reporting those
    # should be enough
    git_add_and_commit(f"Format with monochromatic:{monochromatic_version.version}", repo=repo)

    return current_branch


def format_repos(repos: tuple[Path, ...], options: Namespace) -> None:
    monochromatic_versions = tuple(
        monochromaticVersion(*version.split(":")) for version in options.versions
    )

    for repo in repos:
        from_branch = None
        for monochromatic_version in monochromatic_versions:
            from_branch = format_repo_with_version(
                repo=repo,
                from_branch=from_branch,
                monochromatic_repo=options.monochromatic_repo,
                monochromatic_version=monochromatic_version,
                input_directory=options.input,
            )
        git_switch_branch("main", repo=repo)

    git_switch_branch("main", repo=options.monochromatic_repo)


def main() -> None:
    parser = ArgumentParser(description="""monochromatic Gallery is a script that
    automates the process of applying different monochromatic versions to a selected
    PyPI package and seeing the results between versions.""")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--pypi-package", help="PyPI package to download.")
    group.add_argument(
        "-t", "--top-packages", help="Top n PyPI packages to download.", type=int
    )

    parser.add_argument("-b", "--monochromatic-repo", help="monochromatic's Git repository.", type=Path)
    parser.add_argument(
        "-v",
        "--version",
        help=(
            "Version for given PyPI package. Will be discarded if used with -t option."
        ),
    )
    parser.add_argument(
        "-w",
        "--workers",
        help=(
            "Maximum number of threads to download with at the same time. "
            "Will be discarded if used with -p option."
        ),
    )
    parser.add_argument(
        "-i",
        "--input",
        default=Path("/input"),
        type=Path,
        help="Input directory to read configuration.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=Path("/output"),
        type=Path,
        help="Output directory to download and put result artifacts.",
    )
    parser.add_argument("versions", nargs="*", default=("main",), help="")

    options = parser.parse_args()
    repos = init_repos(options)
    format_repos(repos, options)


if __name__ == "__main__":
    main()
