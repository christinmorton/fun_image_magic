#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Cuts a new release of the image service template: makes code/image_service_template/ an
# exact copy of the files git tracks in code/image_service/, then checks every file matches.
# See docs/template-plan.md. Run from anywhere, with any Python 3:
#   py tools\cut_template.py
# Before running: CHANGELOG.md has an entry for the new version, SERVICE_VERSION matches
# it, the tests pass, and code/image_service/ is committed (so the template matches a commit).
# Files git ignores in the template (.venv, .env, __pycache__, output) are left alone.
import filecmp
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE, TEMPLATE = 'code/image_service/', 'code/image_service_template/'


def git(*args):
    return subprocess.run(['git', *args], cwd=REPO, capture_output=True, check=True).stdout.decode('utf-8')

def files_in(folder):
    # the files on disk in a folder that git would commit (tracked, plus new ones it doesn't
    # ignore), as paths inside that folder, e.g. "api/main.py". A deleted file stays in git's
    # list until the deletion is committed, so only files that exist count.
    listed = git('ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', folder)
    return {path[len(folder):] for path in listed.split('\0') if path and (REPO / path).is_file()}

def remove_empty_folders(folder):
    # folders left empty by deleted files, up to the template folder itself
    while folder != REPO / TEMPLATE and folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
        folder = folder.parent


def main():
    if git('status', '--porcelain', '--', SOURCE).strip():
        sys.exit(f'{SOURCE} has uncommitted changes: commit them first, so the template matches a commit.')
    settings = (REPO / SOURCE / 'api' / 'settings.py').read_text(encoding='utf-8')
    version = re.search(r"SERVICE_VERSION = '([^']+)'", settings).group(1)
    changelog = (REPO / SOURCE / 'CHANGELOG.md').read_text(encoding='utf-8')
    if not re.search(rf'^## {re.escape(version)}\b', changelog, re.MULTILINE):
        sys.exit(f'CHANGELOG.md has no "## {version}" entry: add one before cutting.')

    source = files_in(SOURCE)
    for name in sorted(files_in(TEMPLATE) - source):        # left over from an older release
        (REPO / TEMPLATE / name).unlink()
        remove_empty_folders((REPO / TEMPLATE / name).parent)
    for name in sorted(source):
        target = REPO / TEMPLATE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / SOURCE / name, target)

    # check: the same files, byte for byte
    problems = [f'only in one folder: {name}' for name in sorted(files_in(TEMPLATE) ^ source)]
    problems += [f'different: {name}' for name in sorted(source)
                 if not filecmp.cmp(REPO / SOURCE / name, REPO / TEMPLATE / name, shallow=False)]
    if problems:
        sys.exit('The template does not match:\n  ' + '\n  '.join(problems))
    print(f'Template {version} cut: {len(source)} files copied from {SOURCE} and checked.')
    print(f'Next: run its tests, commit it, and tag image-service-template-v{version}.')


if __name__ == '__main__':
    main()
