#!/usr/bin/env node
/**
 * npm wrapper for transcribe-all.
 * Resolves the downloaded native binary and execs it with all arguments
 * passed through, so the user experience is identical to pip/brew install.
 */

"use strict";

const { spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const binName = process.platform === "win32" ? "transcribe.exe" : "transcribe";
const binPath = path.join(__dirname, binName);

if (!fs.existsSync(binPath)) {
  console.error(
    "\n[transcribe-all] Native binary not found.\n" +
      "  Run: npm install -g transcribe-all  (to reinstall)\n" +
      "  Or:  pip install transcribe-all     (Python install)\n"
  );
  process.exit(1);
}

const result = spawnSync(binPath, process.argv.slice(2), { stdio: "inherit" });

if (result.error) {
  console.error("[transcribe-all] Failed to launch binary:", result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 0);
