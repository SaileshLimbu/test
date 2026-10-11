#!/usr/bin/env python3
"""
Normalize skin zips that contain a stray "ios" folder in the middle of their
path (e.g. "UI/ios/Hero081.unity3d") by removing that "ios" segment and
merging its contents into the parent folder (e.g. "UI/Hero081.unity3d").

Usage:
    python3 scripts/normalize_zip_folders.py              # scan ios/ and android/, fix any zip that needs it
    python3 scripts/normalize_zip_folders.py path/to.zip  # fix specific zip(s) only
    python3 scripts/normalize_zip_folders.py --check       # only report which zips need fixing, change nothing
"""
import sys
import os
import glob
import shutil
import tempfile
import zipfile

BAD_SEGMENT = "ios"


def needs_fix(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            parts = name.split("/")
            dir_parts = parts[:-1]
            if BAD_SEGMENT in dir_parts:
                return True
    return False


def flatten_ios_dirs(root):
    """Bottom-up walk so nested 'ios' dirs are merged before their parents."""
    changed = False
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        if os.path.basename(dirpath) == BAD_SEGMENT:
            parent = os.path.dirname(dirpath)
            for item in os.listdir(dirpath):
                src = os.path.join(dirpath, item)
                dst = os.path.join(parent, item)
                if os.path.exists(dst):
                    if os.path.isdir(src) and os.path.isdir(dst):
                        for sub in os.listdir(src):
                            shutil.move(os.path.join(src, sub), os.path.join(dst, sub))
                        os.rmdir(src)
                        continue
                    else:
                        os.remove(dst)
                shutil.move(src, dst)
            os.rmdir(dirpath)
            changed = True
    return changed


def rezip(root, zip_path):
    fd, tmp_path = tempfile.mkstemp(suffix=".zip", dir=os.path.dirname(zip_path))
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as z:
            for dirpath, dirnames, filenames in os.walk(root):
                for fn in sorted(filenames):
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, root)
                    z.write(full, rel)
        shutil.move(tmp_path, zip_path)
    except Exception:
        os.remove(tmp_path)
        raise


def fix_zip(zip_path):
    tmp_dir = tempfile.mkdtemp(prefix="normalize_")
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp_dir)
        changed = flatten_ios_dirs(tmp_dir)
        if changed:
            rezip(tmp_dir, zip_path)
        return changed
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    args = [a for a in args if a != "--check"]

    if args:
        candidates = args
    else:
        candidates = sorted(glob.glob("ios/*.zip") + glob.glob("android/*.zip"))

    to_fix = [p for p in candidates if needs_fix(p)]

    if not to_fix:
        print("No zips need fixing.")
        return

    print(f"{len(to_fix)} zip(s) need fixing:")
    for p in to_fix:
        print(" -", p)

    if check_only:
        return

    print()
    for p in to_fix:
        fix_zip(p)
        print(f"Fixed: {p}")


if __name__ == "__main__":
    main()
