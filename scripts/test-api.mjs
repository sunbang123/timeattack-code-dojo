import { spawnSync } from "node:child_process";
import { projectRoot, requireVenvPython } from "./python-runtime.mjs";

try {
  const result = spawnSync(
    requireVenvPython(),
    ["-m", "unittest", "discover", "-s", "tests", "-v"],
    { cwd: projectRoot, stdio: "inherit" },
  );
  process.exit(result.status ?? 1);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

