#!/usr/bin/env python3
"""
Rejoin a split zip (Info-Zip "spanned archive": Name.z01, Name.z02, ..., Name.zip)
back into a single, normal, byte-identical zip file.

Needs the "zip" command (Info-Zip) on PATH.

Usage:
    python3 scripts/join_split_zip.py ios/Obsidia_Aspirants.zip [output.zip]
"""
import sys
import subprocess
import os


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    last_part = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(last_part)[0] + ".joined.zip"
    subprocess.run(["zip", "-s", "0", last_part, "--out", out], check=True)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
