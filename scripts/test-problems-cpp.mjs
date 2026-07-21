import { spawnSync } from "node:child_process";
import { projectRoot, requireVenvPython } from "./python-runtime.mjs";

try {
  const result = spawnSync(
    requireVenvPython(),
    [
      "scripts/validate_problem_bank.py",
      "--cpp-local",
      "--output",
      "artifacts/step2-validation-results.json",
    ],
    { cwd: projectRoot, stdio: "inherit" },
  );
  process.exit(result.status ?? 1);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
