#!/usr/bin/env python3

"""Show the latest version and age of all dependencies.

This script helps us keep an overview of which dependencies pinned in the
uv.lock file are out-of-date and how long ago releases were published.

It is run as part of the "deps-upgrade-check" `nox` session.
"""

import datetime
import http.client
import json
import pathlib
import textwrap
import tomllib


PKG_CONSIDERED_OLD = 2  # years after release when a package is considered "old"

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

REPORT_FILE = PROJECT_ROOT / ".cache/dependencies_checked.txt"


def get_direct_dependencies(lock_file: dict) -> dict[str, str]:
    """Map the direct dependencies to "main" or their extra or group.

    `lock_file` is a mapping as returned from `load_lock_file()`.
    """
    root = next(
        pkg for pkg in lock_file["package"] if "editable" in pkg.get("source", {})
    )
    labels = {dep["name"]: "main" for dep in root.get("dependencies", [])}

    for kind in ("optional-dependencies", "dev-dependencies"):
        for label, deps in root.get(kind, {}).items():
            for dep in deps:
                labels.setdefault(dep["name"], label)

    return labels


def get_pinned_packages(lock_file: dict) -> dict[str, str]:
    """Map all packages from PyPI to their versions.

    `lock_file` is a mapping as returned from `load_lock_file()`.
    """
    return {
        pkg["name"]: pkg["version"]
        for pkg in lock_file["package"]
        if "registry" in pkg.get("source", {})
    }


def get_years_since_release(
    package_name: str,
    pinned_version: str,
) -> tuple[float | None, str | None]:
    """Get the years since the pinned release and the latest version."""
    conn = http.client.HTTPSConnection("pypi.org")
    conn.request("GET", f"/pypi/{package_name}/json")

    response = conn.getresponse()

    if response.status != 200:
        return None, None

    data = json.loads(response.read().decode())

    all_releases_on_pypi = data.get("releases", {})
    infos_for_pinned_release = all_releases_on_pypi.get(pinned_version, [])

    if not infos_for_pinned_release:
        return None, None

    latest_version = data["info"]["version"]

    release_date = infos_for_pinned_release[0]["upload_time"]
    release_date = datetime.datetime.fromisoformat(release_date.replace("Z", "+00:00"))

    years_since_release = (datetime.datetime.now() - release_date).days / 365.25

    return round(years_since_release, 1), latest_version


def load_lock_file() -> dict:
    """Load the uv.lock file."""
    return tomllib.loads((PROJECT_ROOT / "uv.lock").read_text())


def make_comment(
    pinned_version: str,
    years_since_release: float | None,
    latest_version: str | None,
) -> tuple[str, bool]:
    """Describe a pinned package and decide if it is shown on the CLI."""
    if years_since_release is None:
        return "no info on PyPI", True

    is_latest = pinned_version == latest_version

    if is_latest:
        comment = "up-to-date"
    else:
        comment = f"< {latest_version:<8}"

    if years_since_release > PKG_CONSIDERED_OLD:
        comment += f"       {years_since_release} years ago"

    print_to_cli = not is_latest or years_since_release > PKG_CONSIDERED_OLD

    return comment.strip(), print_to_cli


def write_report(lines: list[tuple[str, bool]]) -> None:
    """Write all lines to the report file and the noteworthy ones to the CLI."""
    header = f"""
    # Created on: {datetime.date.today()}
    #
    # The versions pinned in the uv.lock file are amended with information
    # regarding the latest available version on PyPI and the no. of years
    # that have passed since the pinned version was released on PyPI,
    # if > {PKG_CONSIDERED_OLD} year(s).
    #
    # The purpose of these information is to judge whether
    # time should be invested to upgrade further dependencies,
    # which likely requires rewriting some of the code.
    #
    #
    """

    titles = (
        f"# {'Package (pinned)':<40}  {'Direct':<10}"
        f"{'PyPI (latest)':<17}Released (pinned)"
    )

    header = (
        textwrap.dedent(header)[1:] + titles + "\n#" + "=" * (len(titles) - 1) + "\n"
    )

    REPORT_FILE.parent.mkdir(exist_ok=True)

    with REPORT_FILE.open("w") as f:
        f.write(header)

        print(header, end="")

        for line, print_to_cli in lines:
            f.write(line)

            if print_to_cli:
                print(line, end="")


def check_all_pinned_packages() -> None:
    """Check all packages from PyPI that are pinned in the uv.lock file."""
    lock_file = load_lock_file()
    direct_dependencies = get_direct_dependencies(lock_file)

    lines = []

    for package, pinned_version in sorted(get_pinned_packages(lock_file).items()):
        years_since_release, latest_version = get_years_since_release(
            package,
            pinned_version,
        )

        comment, print_to_cli = make_comment(
            pinned_version,
            years_since_release,
            latest_version,
        )

        requirement = f"{package}=={pinned_version}"
        direct = direct_dependencies.get(package, "")

        lines.append((f"{requirement:<40}  # {direct:<10}{comment}\n", print_to_cli))

    write_report(lines)


if __name__ == "__main__":
    check_all_pinned_packages()
