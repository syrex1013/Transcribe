#!/usr/bin/env node
/**
 * Postinstall script for transcribe-all npm package.
 *
 * Downloads the correct pre-built binary for the current platform/arch
 * from GitHub Releases and places it next to the JS wrapper in bin/.
 */

"use strict";

const https = require("https");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const PKG = require("../package.json");
const VERSION = PKG.version;
const REPO = "syrex1013/Transcribe";
const BIN_DIR = path.join(__dirname, "..", "bin");

// ─── Platform / architecture resolution ──────────────────────────────────────

const PLATFORM_MAP = {
  linux: "linux",
  darwin: "darwin",
  win32: "windows",
};

const ARCH_MAP = {
  x64: "x64",
  arm64: "arm64",
};

// Supported build matrix: linux-x64, darwin-arm64, windows-x64
const SUPPORTED = new Set(["linux-x64", "darwin-arm64", "windows-x64"]);

function getAssetName() {
  const p = PLATFORM_MAP[process.platform];
  const a = ARCH_MAP[process.arch];
  const key = `${p || process.platform}-${a || process.arch}`;

  if (!p || !a || !SUPPORTED.has(key)) {
    throw new Error(
      `No pre-built binary for ${process.platform}/${process.arch} (${key}). ` +
        "Install via pip instead: pip install transcribe-all"
    );
  }

  const ext = process.platform === "win32" ? ".exe" : "";
  const pName = p === "win32" ? "windows" : p;
  return `transcribe-${pName}-${a}${ext}`;
}

// ─── HTTP download with redirect following ───────────────────────────────────

function download(url, destPath, redirectsLeft = 5) {
  return new Promise((resolve, reject) => {
    if (redirectsLeft === 0) {
      return reject(new Error(`Too many redirects for ${url}`));
    }

    https
      .get(url, { headers: { "User-Agent": `transcribe-all/${VERSION}` } }, (res) => {
        if (res.statusCode === 301 || res.statusCode === 302 || res.statusCode === 307) {
          return resolve(download(res.headers.location, destPath, redirectsLeft - 1));
        }
        if (res.statusCode !== 200) {
          return reject(
            new Error(
              `Download failed with HTTP ${res.statusCode} for ${url}\n` +
                "Check that the release exists at: " +
                `https://github.com/${REPO}/releases/tag/v${VERSION}`
            )
          );
        }

        const tmpPath = destPath + ".tmp";
        const file = fs.createWriteStream(tmpPath);
        res.pipe(file);
        file.on("finish", () => {
          file.close(() => {
            fs.renameSync(tmpPath, destPath);
            resolve();
          });
        });
        file.on("error", (err) => {
          fs.unlink(tmpPath, () => {});
          reject(err);
        });
      })
      .on("error", reject);
  });
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  // Skip download during local development (when running from source)
  if (process.env.TRANSCRIBE_SKIP_POSTINSTALL === "1") {
    console.log("[transcribe-all] Skipping binary download (TRANSCRIBE_SKIP_POSTINSTALL=1).");
    return;
  }

  let assetName;
  try {
    assetName = getAssetName();
  } catch (err) {
    console.warn(`\n[transcribe-all] ${err.message}\n`);
    process.exit(0); // Non-fatal: pip fallback is available
  }

  const binName = process.platform === "win32" ? "transcribe.exe" : "transcribe";
  const destPath = path.join(BIN_DIR, binName);

  const url = `https://github.com/${REPO}/releases/download/v${VERSION}/${assetName}`;
  console.log(`\n[transcribe-all] Downloading ${assetName} for ${process.platform}/${process.arch}…`);
  console.log(`  From: ${url}\n`);

  try {
    await download(url, destPath);

    // Make binary executable on Unix
    if (process.platform !== "win32") {
      fs.chmodSync(destPath, 0o755);
    }

    console.log(`[transcribe-all] ✔  Installed to ${destPath}\n`);
    console.log('  Run:  transcribe --help\n');
  } catch (err) {
    console.error(
      `\n[transcribe-all] ✖  Binary download failed: ${err.message}\n` +
        "  Fallback: pip install transcribe-all\n"
    );
    process.exit(0); // Non-fatal exit so npm install doesn't fail hard
  }
}

main();
