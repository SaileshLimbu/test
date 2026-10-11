#!/usr/bin/env python3
"""
Normalizes skin zips to one layout, the same one Alpha_Legend.zip already uses:

    <Zip_Name>/Art/...
    <Zip_Name>/Audio/...
    <Zip_Name>/UI/...

Fixes applied to each zip in ios/ and android/:
  1. Root layout: a zip with Art/, Audio/ or UI/ at the top level gets them wrapped in a folder named after
     the zip. Other top-level items (e.g. "Document/") are removed, since they are not skin content.
  2. Stray "ios" folder in the middle of a path ("UI/ios/Hero081.unity3d") is removed, merging its contents
     into the parent folder ("UI/Hero081.unity3d").
  3. Junk entries are removed: hidden files and folders (.DS_Store, ".[ Free Script ... ]") and __MACOSX.

Usage:
    python3 scripts/normalize_zip_folders.py              # fix every zip in ios/ and android/
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
ROOTS = {"Art", "Audio", "UI"}


def entries(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        return [n for n in z.namelist() if not n.endswith("/")]


def is_junk(name):
    return any(part.startswith(".") or part == "__MACOSX" for part in name.split("/") if part)


def reasons(zip_path):
    """Why a zip needs fixing (empty list = already normalized)."""
    names = entries(zip_path)
    out = []
    if any(n.split("/")[0] in ROOTS for n in names):
        out.append("root layout (Art/UI/Audio not inside a folder)")
    if any(BAD_SEGMENT in n.split("/")[:-1] for n in names):
        out.append("stray 'ios' folder")
    if any(is_junk(n) for n in names):
        out.append("junk files")
    return out


def remove_junk(root):
    removed = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        for d in list(dirnames):
            if d.startswith(".") or d == "__MACOSX":
                shutil.rmtree(os.path.join(dirpath, d))
                removed.append(os.path.relpath(os.path.join(dirpath, d), root))
                dirnames.remove(d)
        for f in filenames:
            if f.startswith("."):
                os.remove(os.path.join(dirpath, f))
                removed.append(os.path.relpath(os.path.join(dirpath, f), root))
    return removed


def wrap_root_layout(root, folder_name):
    """Moves Art/Audio/UI under <root>/<folder_name>/ and drops any other top-level items."""
    top = os.listdir(root)
    if not any(t in ROOTS for t in top):
        return [], False
    dropped = [t for t in top if t not in ROOTS]
    for t in dropped:
        p = os.path.join(root, t)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    target = os.path.join(root, folder_name)
    os.makedirs(target, exist_ok=True)
    for t in top:
        if t in ROOTS:
            shutil.move(os.path.join(root, t), os.path.join(target, t))
    return dropped, True


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
    """Returns the list of things removed from the zip (empty if nothing changed)."""
    stem = os.path.splitext(os.path.basename(zip_path))[0]
    tmp_dir = tempfile.mkdtemp(prefix="normalize_")
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp_dir)
        removed = remove_junk(tmp_dir)
        dropped, wrapped = wrap_root_layout(tmp_dir, stem)
        removed += dropped
        changed = flatten_ios_dirs(tmp_dir) or wrapped or bool(removed)
        if changed:
            rezip(tmp_dir, zip_path)
        return removed
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

    to_fix = [(p, reasons(p)) for p in candidates]
    to_fix = [(p, r) for p, r in to_fix if r]

    if not to_fix:
        print("No zips need fixing.")
        return

    print(f"{len(to_fix)} zip(s) need fixing:")
    for p, r in to_fix:
        print(f" - {p}: {', '.join(r)}")

    if check_only:
        return

    print()
    for p, _ in to_fix:
        removed = fix_zip(p)
        note = f" (removed: {', '.join(removed)})" if removed else ""
        print(f"Fixed: {p}{note}")


if __name__ == "__main__":
    main()
