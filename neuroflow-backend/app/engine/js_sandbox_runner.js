"use strict";
// Runs one Code-node snippet inside a fresh V8 context created via the
// built-in `vm` module. Spawned as a standalone subprocess by
// app/engine/code_sandbox.py -- never runs in the worker's own event loop.
// See docs/12-execution-engine.md #12.7 and docs/15-security-and-credentials.md
// #15.8: process isolation, no `require`/`fs`/`process` inside the sandboxed
// context (they are simply never added to it, so they resolve to
// `undefined`), and a per-script wall-clock timeout enforced by `vm` itself.
//
// Communication is stdin (one JSON payload) / stdout (one JSON result) --
// no temp files.

const vm = require("vm");

const SCRIPT_TIMEOUT_MS = 25000; // < the 30s hard wall-clock cap enforced
// again, from outside, by code_sandbox.py -- this is the inner, faster trip.

function buildSandbox(extra, allowNetwork) {
  const sandbox = { JSON, Math, Date, console: { log: () => {} }, ...extra };
  if (allowNetwork && typeof fetch === "function") {
    sandbox.fetch = fetch;
  }
  return sandbox;
}

function runOne(code, extra, allowNetwork) {
  const context = vm.createContext(buildSandbox(extra, allowNetwork));
  const script = new vm.Script(code, { filename: "code-node.js" });
  return script.runInContext(context, { timeout: SCRIPT_TIMEOUT_MS });
}

function main() {
  let input = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => {
    input += chunk;
  });
  process.stdin.on("end", () => {
    let payload;
    try {
      payload = JSON.parse(input);
    } catch (err) {
      process.stdout.write(JSON.stringify({ ok: false, error: "Invalid input: " + err.message }));
      process.exitCode = 1;
      return;
    }
    const { code, items, mode, allowNetwork } = payload;
    try {
      let result;
      if (mode === "perItem") {
        result = items.map((item) => runOne(code, { item }, allowNetwork));
      } else {
        result = runOne(code, { items }, allowNetwork);
      }
      process.stdout.write(JSON.stringify({ ok: true, result }));
    } catch (err) {
      process.stdout.write(JSON.stringify({ ok: false, error: String((err && err.message) || err) }));
      process.exitCode = 1;
    }
  });
}

main();
