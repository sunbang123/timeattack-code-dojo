import { spawn } from "node:child_process";
import { projectRoot, requireVenvPython } from "./python-runtime.mjs";

try {
  const child = spawn(requireVenvPython(), ["api/index.py"], {
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

