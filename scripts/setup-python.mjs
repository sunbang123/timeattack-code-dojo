import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { findSystemPython, projectRoot, requireVenvPython, venvPython } from "./python-runtime.mjs";

function run(command, args) {
  const result = spawnSync(command, args, { cwd: projectRoot, stdio: "inherit" });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

if (!existsSync(venvPython())) {
  const python = findSystemPython();
  run(python.command, [...python.prefix, "-m", "venv", ".venv"]);
}

run(requireVenvPython(), ["-m", "pip", "install", "-r", "requirements.txt"]);

