#!/usr/bin/env bash
#
# Give the sandbox a working Chromium for UI testing.
#
# Why this exists: every browser CDN is firewalled in this environment
# (cdn.playwright.dev -> ECONNRESET, storage.googleapis.com and deb.debian.org
# -> no route), so `npx playwright install` cannot work. The npm registry IS
# reachable, and @sparticuz/chromium ships the browser binary and the shared
# libraries it needs inside its own npm tarball, so it can be installed with
# nothing but npm.
#
#   bash tools/browser-setup.sh
#
# Prints the LD_LIBRARY_PATH you must export when launching the browser.
# Idempotent: re-running skips work that is already done.
set -euo pipefail

WORKDIR="${UITEST_DIR:-/home/user/uitest}"
CHROMIUM="$WORKDIR/bin/chromium"
LIBDIR="$WORKDIR/al2023/lib"

export LD_LIBRARY_PATH="$LIBDIR"

if [ -x "$CHROMIUM" ] && "$CHROMIUM" --version >/dev/null 2>&1; then
  echo ">> Chromium already usable: $("$CHROMIUM" --version)"
  echo ">> export LD_LIBRARY_PATH=$LIBDIR"
  exit 0
fi

echo ">> Setting up Chromium in $WORKDIR ..."
mkdir -p "$WORKDIR"
cd "$WORKDIR"
[ -f package.json ] || npm init -y >/dev/null 2>&1

npm install --no-audit --no-fund \
  playwright@1.64.0 @sparticuz/chromium

# The binary is brotli-compressed inside the package. Node's zlib decompresses
# it without needing the `brotli` CLI, which is not installed here.
echo ">> Decompressing the binary ..."
mkdir -p bin
node -e '
  const fs = require("fs"), zlib = require("zlib");
  fs.writeFileSync(
    "bin/chromium",
    zlib.brotliDecompressSync(
      fs.readFileSync("node_modules/@sparticuz/chromium/bin/chromium.br")
    )
  );
'
chmod +x bin/chromium

# Chromium needs libnspr4, libnss3 and friends, none of which are on this
# image. The package bundles the Amazon Linux 2023 copies.
echo ">> Unpacking bundled shared libraries ..."
node -e '
  const fs = require("fs"), zlib = require("zlib");
  fs.writeFileSync(
    "/tmp/al2023.tar",
    zlib.brotliDecompressSync(
      fs.readFileSync("node_modules/@sparticuz/chromium/bin/al2023.tar.br")
    )
  );
'
mkdir -p al2023
tar -xf /tmp/al2023.tar -C al2023 2>/dev/null || true
rm -f /tmp/al2023.tar

echo ">> Verifying ..."
if "$CHROMIUM" --version 2>/dev/null; then
  echo
  echo ">> Ready. When launching Playwright, use:"
  echo "     executablePath: \"$CHROMIUM\""
  echo "     and export LD_LIBRARY_PATH=$LIBDIR"
  echo "     launch args: [\"--no-sandbox\", \"--disable-dev-shm-usage\", \"--disable-gpu\"]"
else
  echo "!! Chromium failed to run. Shared libraries found:"
  find "$WORKDIR/al2023" -name '*.so*' 2>/dev/null | head
  exit 1
fi
