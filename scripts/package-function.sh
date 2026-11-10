#!/usr/bin/env bash
# Build the deployment archive from project-owned Python modules only.
# The runtime supplies the object storage client, so no third-party
# libraries are installed into the archive.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$REPO_ROOT/src/functions/src"
BUILD_DIR="$REPO_ROOT/build"
PKG_DIR="$BUILD_DIR/package"
ZIP_PATH="$BUILD_DIR/function.zip"

echo "[1/3] Preparing build directory ..."
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR"
rm -f "$ZIP_PATH"

echo "[2/3] Copying function modules ..."
cp "$SRC_DIR"/*.py "$PKG_DIR/"

echo "[3/3] Assembling deployment archive ..."
python - "$PKG_DIR" "$ZIP_PATH" <<'PY'
import sys, zipfile
from pathlib import Path

pkg_dir, zip_path = Path(sys.argv[1]), Path(sys.argv[2])
files = sorted(p for p in pkg_dir.rglob("*") if p.is_file() and p.suffix == ".py")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, path.relative_to(pkg_dir).as_posix())
print("archive=%s files=%d bytes=%d" % (
    zip_path.as_posix(), len(files), zip_path.stat().st_size))
for path in files:
    print("   ", path.relative_to(pkg_dir).as_posix())
PY

echo "Done: $ZIP_PATH"
