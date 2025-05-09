#!/usr/bin/env python3

import json
import logging
import subprocess
from argparse import ArgumentParser, Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from sys import exit
from typing import Optional


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--check",
        help="only check for files requiring formatting; don't actually format them",
        action="store_true",
        default=False,
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    git_parser = subparsers.add_parser(
        "git", help="Apply format to changes tracked by git"
    )
    git_parser.add_argument(
        "--source",
        help=(
            "consider files modified in the specified commit-ish; "
            "if not specified, defaults to all changes in the working directory"
        ),
        type=str,
        required=False,
        default=None,
    )
    git_parser.add_argument(
        "--target",
        help="consider files modified since the specified commit-ish; defaults to HEAD",
        type=str,
        required=False,
        default="HEAD",
    )
    git_parser.add_argument(
        "--staged",
        help="consider files with staged modifications only",
        action="store_true",
        default=False,
    )
    options = parser.parse_args()
    if (
        options.subcommand == "git"
        and options.staged
        and (options.source is not None or options.target != "HEAD")
    ):
        logging.error(
            "--staged cannot be used with --source or --target; "
            "use --staged with --source=HEAD"
        )
        exit(1)
    return options


def filter_files_by_globs(
    files: list[Path], dir_path: Path, globs: tuple[str, ...], excludes: tuple[str, ...]
) -> list[Path]:
    return [
        file
        for file in files
        if file.is_relative_to(dir_path)
        and matches_any_glob(globs, file)
        and not relative_to_any(excludes, file)
    ]


def relative_to_any(excludes: tuple[str, ...], file: Path) -> bool:
    return any(file.is_relative_to(exclude) for exclude in excludes)


def matches_any_glob(globs: tuple[str, ...], file: Path) -> bool:
    return any(file.match(glob) for glob in globs)


def run_bazel_tool(tool_name: str, args: list[str]) -> subprocess.CompletedProcess:
    # Use the formatter executable from bazel-bin
    bazel_bin = Path("bazel-bin")
    tool_suffix = Path("build") / "deps" / "formatters" / tool_name
    internal_tool_path = bazel_bin / "external" / "workerd" / tool_suffix
    workerd_tool_path = bazel_bin / tool_suffix

    if internal_tool_path.exists():
        return subprocess.run([internal_tool_path, *args])
    if workerd_tool_path.exists():
        return subprocess.run([workerd_tool_path, *args])

    # Use the new formatter targets in build/deps/formatters
    build_target = f"@workerd//build/deps/formatters:{tool_name}@rule"
    download_result = subprocess.run(["bazel", "build", build_target])
    if download_result.returncode != 0:
        logging.error(f"Failed to download {tool_name}")
        return download_result

    if internal_tool_path.exists():
        return subprocess.run([internal_tool_path, *args])
    else:
        return subprocess.run([workerd_tool_path, *args])


def clang_format(files: list[Path], check: bool = False) -> bool:
    if check:
        cmd = ["--dry-run", "--Werror"]
    else:
        cmd = ["-i"]
    result = run_bazel_tool("clang-format", cmd + files)
    return result.returncode == 0


def prettier(files: list[Path], check: bool = False) -> bool:
    PRETTIER = "bazel-bin/node_modules/prettier/bin/prettier.cjs"

    if not Path(PRETTIER).exists():
        subprocess.run(["bazel", "build", "//:node_modules/prettier"])

    cmd = [PRETTIER, "--log-level=warn", "--check" if check else "--write"]
    result = subprocess.run(cmd + files)
    return result.returncode == 0


def buildifier(files: list[Path], check: bool = False) -> bool:
    cmd = ["--mode=check" if check else "--mode=fix"]
    result = run_bazel_tool("buildifier", cmd + files)
    return result.returncode == 0


def ruff(files: list[Path], check: bool = False) -> bool:
    if not files:
        return True

    cmd = ["check"]
    if not check:
        cmd.append("--fix")
    result1 = run_bazel_tool("ruff", cmd + files)

    # format
    cmd = ["format"]
    if check:
        cmd.append("--diff")

    result2 = run_bazel_tool("ruff", cmd + files)
    return result1.returncode == 0 and result2.returncode == 0


def git_get_modified_files(
    target: str, source: Optional[str], staged: bool
) -> list[Path]:
    if staged:
        files_in_diff = subprocess.check_output(
            ["git", "diff", "--diff-filter=d", "--name-only", "--cached"],
            encoding="utf-8",
        ).splitlines()
        return [Path(file) for file in files_in_diff]
    else:
        merge_base = subprocess.check_output(
            ["git", "merge-base", target, source or "HEAD"], encoding="utf-8"
        ).strip()
        files_in_diff = subprocess.check_output(
            ["git", "diff", "--diff-filter=d", "--name-only", merge_base]
            + ([source] if source else []),
            encoding="utf-8",
        ).splitlines()
        return [Path(file) for file in files_in_diff]


def git_get_all_files() -> list[Path]:
    files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        encoding="utf-8",
    ).splitlines()
    return [Path(file) for file in files]


@dataclass
class FormatConfig:
    directory: str
    globs: tuple[str, ...]
    formatter: str
    excludes: tuple[str, ...] = ()


FORMATTERS = {
    "clang-format": clang_format,
    "prettier": prettier,
    "ruff": ruff,
    "buildifier": buildifier,
}


def format(config: FormatConfig, files: list[Path], check: bool) -> tuple[bool, str]:
    matching_files = filter_files_by_globs(
        files, Path(config.directory), config.globs, config.excludes
    )

    if not matching_files:
        return (
            True,
            f"No matching files for {config.directory} ({', '.join(config.globs)})",
        )

    result = FORMATTERS[config.formatter](matching_files, check)
    message = (
        f"{len(matching_files)} files in {config.directory} ({', '.join(config.globs)})"
    )
    return (
        result,
        f"{'Checked' if check else 'Formatted'} {message}",
    )


def main() -> None:
    options = parse_args()

    if options.subcommand == "git":
        files = git_get_modified_files(options.target, options.source, options.staged)
    else:
        files = git_get_all_files()

    with (Path(__file__).parent / "format.json").open() as fp:
        configs = json.load(fp, object_hook=lambda o: FormatConfig(**o))

    all_ok = True

    with ThreadPoolExecutor() as executor:
        future_to_config = {
            executor.submit(format, config, files, options.check): config
            for config in configs
        }
        for future in as_completed(future_to_config):
            config = future_to_config[future]
            try:
                result, message = future.result()
                all_ok &= result
                logging.info(message)
            except Exception:
                logging.exception(
                    f"Formatter for {config.directory} generated an exception"
                )
                all_ok = False

    if not all_ok:
        logging.error(
            "Code has linting issues. Fix with python ./tools/cross/format.py"
        )
        exit(1)


if __name__ == "__main__":
    main()
