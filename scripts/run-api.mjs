import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { projectRoot, requireVenvPython } from "./python-runtime.mjs";

function loadLocalEnvironment() {
  for (const filename of [".env.local", ".env"]) {
    const path = resolve(projectRoot, filename);
    if (!existsSync(path)) continue;
    for (const rawLine of readFileSync(path, "utf8").split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      const separator = line.indexOf("=");
      if (separator < 1) continue;
      const key = line.slice(0, separator).trim();
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key) || process.env[key] !== undefined) continue;
      let value = line.slice(separator + 1).trim();
      if (value.length >= 2 && value[0] === value.at(-1) && ['"', "'"].includes(value[0])) {
        value = value.slice(1, -1);
      }
      process.env[key] = value;
    }
  }
}

try {
  loadLocalEnvironment();
  const child = spawn(requireVenvPython(), ["-m", "api.index"], {
    cwd: projectRoot,
    env: process.env,
    stdio: "inherit",
  });

  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => child.kill(signal));
  }

  child.on("exit", (code) => process.exit(code ?? 0));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
