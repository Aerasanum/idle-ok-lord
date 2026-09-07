#!/usr/bin/env node
// Client acceptance check — "app boots in Expo Go" scenario (I15 remote push must never be imported eagerly).
// 1) Static scan: `expo-notifications` may only be referenced by src/push/adapter.ts, through a dynamic import().
// 2) Metro bundle graph (android + ios): the expo-notifications module must have exactly one dependent (the adapter)
//    and that dependency must be an async require, so Expo Go never evaluates the module.
// Usage: node scripts/expo-go-acceptance.mjs   (env METRO_URL, default http://localhost:3000)
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname.replace(/\/$/, "");
const METRO = process.env.METRO_URL ?? "http://localhost:3000";
const ADAPTER = "src/push/adapter.ts";
const failures = [];
const ok = (msg) => console.log(`  ✓ ${msg}`);
const fail = (msg) => { failures.push(msg); console.log(`  ✗ ${msg}`); };

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.(ts|tsx|js|jsx|mjs)$/.test(name)) out.push(p);
  }
  return out;
}

console.log("1) Static scan (app/, src/)");
const files = [...walk(join(ROOT, "app")), ...walk(join(ROOT, "src"))];
let adapterSeen = false;
for (const f of files) {
  const rel = relative(ROOT, f);
  const src = readFileSync(f, "utf8");
  const staticImport = /^\s*import\s[^;]*?from\s+["']expo-notifications["']/m.test(src) || /require\(\s*["']expo-notifications["']\s*\)/.test(src);
  const dynamicImport = /import\(\s*["']expo-notifications["']\s*\)/.test(src);
  if (rel === ADAPTER) {
    adapterSeen = true;
    if (staticImport) fail(`${rel}: static import of expo-notifications`);
    if (!dynamicImport) fail(`${rel}: dynamic import() of expo-notifications missing`);
    if (!/ExecutionEnvironment\.StoreClient/.test(src)) fail(`${rel}: Expo Go guard (ExecutionEnvironment.StoreClient) missing`);
  } else if (staticImport || dynamicImport) {
    fail(`${rel}: references expo-notifications directly (must go through ${ADAPTER})`);
  }
}
if (!adapterSeen) fail(`${ADAPTER} not found`);
if (!failures.length) ok(`only ${ADAPTER} references expo-notifications, via guarded dynamic import`);
// react-native-purchases (RevenueCat) is native-only as well: must stay behind the Expo Go guard in src/billing.ts
for (const f of files) {
  const rel = relative(ROOT, f);
  const src = readFileSync(f, "utf8");
  if (/^\s*import\s[^;]*?from\s+["']react-native-purchases["']/m.test(src)) fail(`${rel}: static import of react-native-purchases (Expo Go has no native module)`);
  else if (rel === "src/billing.ts" && !/storeClient/.test(src)) fail(`${rel}: Expo Go guard missing around react-native-purchases`);
}
if (!failures.length) ok("react-native-purchases only loaded lazily behind the Expo Go guard (src/billing.ts)");

console.log("2) Metro bundle graph");
for (const platform of ["android", "ios"]) {
  const url = `${METRO}/node_modules/expo-router/entry.bundle?platform=${platform}&dev=true&minify=false`;
  let text;
  try {
    const res = await fetch(url);
    if (!res.ok) { fail(`${platform}: bundle HTTP ${res.status}`); continue; }
    text = await res.text();
  } catch (e) {
    fail(`${platform}: cannot fetch bundle (${e.message}) — is Metro running at ${METRO}?`);
    continue;
  }
  if (!text.includes(`"app/_layout.tsx"`)) { fail(`${platform}: app/_layout.tsx not in bundle`); continue; }
  ok(`${platform}: bundle compiled (${(text.length / 1e6).toFixed(1)} MB), app/_layout.tsx present`);
  // module footer format: },<id>,[<deps>],"<name>");
  const footer = /\},(\d+),\[([\d,]*)\],"([^"]+)"\);/g;
  const modules = [];
  let m;
  while ((m = footer.exec(text))) modules.push({ id: Number(m[1]), deps: m[2] ? m[2].split(",").map(Number) : [], name: m[3], end: m.index });
  const notif = modules.find((x) => x.name === "node_modules/expo-notifications/build/index.js");
  if (!notif) { ok(`${platform}: expo-notifications not bundled at all`); continue; }
  const dependents = modules.filter((x) => x.deps.includes(notif.id));
  const names = dependents.map((x) => x.name);
  if (names.length !== 1 || names[0] !== ADAPTER) fail(`${platform}: expo-notifications dependents = [${names.join(", ")}] (expected only ${ADAPTER})`);
  else {
    const adapter = dependents[0];
    const prev = modules.filter((x) => x.end < adapter.end).sort((a, b) => b.end - a.end)[0];
    const body = text.slice(prev ? prev.end : 0, adapter.end);
    const k = adapter.deps.indexOf(notif.id);
    const eager = new RegExp(`(?<!async-require-module"\\)\\()require\\(_dependencyMap\\[${k}\\]`).test(body);
    const lazy = new RegExp(`async-require-module"\\)\\(_dependencyMap\\[${k}\\]`).test(body);
    if (eager || !lazy) fail(`${platform}: adapter requires expo-notifications eagerly`);
    else ok(`${platform}: expo-notifications only reachable through async require in ${ADAPTER}`);
  }
}

console.log(failures.length ? `\nFAILED (${failures.length})` : "\nPASS — Expo Go boot scenario acceptance satisfied");
process.exit(failures.length ? 1 : 0);
