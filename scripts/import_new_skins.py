#!/usr/bin/env python3
"""
Import a raw skin archive (.zip or .rar) dropped in the project root into
ios/<Hero>_<Skin>.zip, normalized to the same layout the rest of the repo
uses (<Hero>_<Skin>/Art|Audio|UI/..., no nested "ios" folder, no junk files),
and register it in manifest.json.

Usage:
    python3 scripts/import_new_skins.py <archive> <Hero> <Skin> [--platform ios|android]

Example:
    python3 scripts/import_new_skins.py "Obsidia Aspirants.zip" Obsidia Aspirants
"""
import sys
import os
import json
import shutil
import subprocess
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
from normalize_zip_folders import remove_junk, flatten_ios_dirs, rezip, ROOTS  # noqa: E402


def extract(archive, dest):
    if archive.lower().endswith(".rar"):
        subprocess.run(
            ["unar", "-f", "-D", "-q", "-o", dest, archive], check=True
        )
    else:
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)


def normalize_wrapper(root, folder_name):
    """Collapses whatever sits at the top of the extracted archive down to a
    single <folder_name>/ containing just Art/Audio/UI, wherever they are."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for d in dirnames:
            if d in ROOTS and d not in found:
                found[d] = os.path.join(dirpath, d)

    target = os.path.join(root, folder_name)
    if os.path.abspath(target) != os.path.abspath(root):
        os.makedirs(target, exist_ok=True)

    for name, path in found.items():
        dst = os.path.join(target, name)
        if os.path.abspath(path) != os.path.abspath(dst):
            shutil.move(path, dst)

    # drop everything else at the real root except our target folder
    for item in os.listdir(root):
        full = os.path.join(root, item)
        if os.path.abspath(full) == os.path.abspath(target):
            continue
        shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)


def import_skin(archive, hero, skin, platform="ios"):
    base = f"{hero}_{skin}"
    dest_zip = os.path.join(platform, base + ".zip")
    tmp_dir = tempfile.mkdtemp(prefix="import_")
    try:
        extract(archive, tmp_dir)
        remove_junk(tmp_dir)
        normalize_wrapper(tmp_dir, base)
        flatten_ios_dirs(tmp_dir)
        remove_junk(tmp_dir)
        rezip(tmp_dir, dest_zip)
        with zipfile.ZipFile(dest_zip) as z:
            n_files = len(z.namelist())
        n_bytes = os.path.getsize(dest_zip)
        return {
            "file": dest_zip,
            "platform": platform,
            "hero": hero,
            "skin": skin,
            "files": n_files,
            "bytes": n_bytes,
            "source": os.path.basename(archive),
            "image": None,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    args = sys.argv[1:]
    platform = "ios"
    if "--platform" in args:
        i = args.index("--platform")
        platform = args[i + 1]
        del args[i : i + 2]

    if len(args) != 3:
        print(__doc__)
        sys.exit(1)

    archive, hero, skin = args
    entry = import_skin(archive, hero, skin, platform)

    manifest_path = "manifest.json"
    manifest = json.load(open(manifest_path))
    manifest.append(entry)
    json.dump(manifest, open(manifest_path, "w"), indent=2)

    print(f"Added {entry['file']} ({entry['files']} files, {entry['bytes']} bytes)")


if __name__ == "__main__":
    main()
