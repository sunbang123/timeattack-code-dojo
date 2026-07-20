import { existsSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

export const projectRoot = process.cwd();

export function venvPython() {
  return path.join(
    projectRoot,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
}

export function findSystemPython() {
  const candidates = [
    process.env.PYTHON ? { command: process.env.PYTHON, prefix: [] } : null,
    { command: "python", prefix: [] },
    { command: "python3", prefix: [] },
    process.platform === "win32" ? { command: "py", prefix: ["-3"] } : null,
    process.platform === "win32"
      ? {
          command: path.join(
            homedir(),
            ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe",
          ),
          prefix: [],
        }
      : null,
  ].filter(Boolean);

  for (const candidate of candidates) {
    const result = spawnSync(candidate.command, [...candidate.prefix, "--version"], {
      stdio: "ignore",
    });
    if (result.status === 0) {
      return candidate;
    }
  }

  throw new Error(
    "Python 3를 찾을 수 없습니다. Python을 설치하거나 PYTHON 환경 변수를 지정해 주세요.",
  );
}

export function requireVenvPython() {
  const executable = venvPython();
  if (!existsSync(executable)) {
    throw new Error(".venv가 없습니다. 먼저 `pnpm setup:python`을 실행해 주세요.");
  }
  return executable;
}

