import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const projectRoot = process.cwd();
const problemBankRoot = path.join(projectRoot, "problem_bank");
const manifest = JSON.parse(
  readFileSync(path.join(problemBankRoot, "manifest.json"), "utf8"),
);

if (!Array.isArray(manifest.problems)) {
  throw new Error("Problem bank manifest must contain a problems array.");
}

const publicProblems = {};
const privateProblems = {};

for (const entry of manifest.problems) {
  const problemId = entry?.id;
  if (typeof problemId !== "string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(problemId)) {
    throw new Error("Problem bank manifest contains an invalid problem id.");
  }
  if (publicProblems[problemId] || privateProblems[problemId]) {
    throw new Error(`Problem bank manifest contains a duplicate id: ${problemId}`);
  }

  publicProblems[problemId] = JSON.parse(
    readFileSync(path.join(problemBankRoot, "public", `${problemId}.json`), "utf8"),
  );
  privateProblems[problemId] = JSON.parse(
    readFileSync(path.join(problemBankRoot, "private", `${problemId}.json`), "utf8"),
  );
}

const outputPath = path.join(problemBankRoot, "bundle.json");
const bundle = {
  manifest,
  public: publicProblems,
  private: privateProblems,
};

writeFileSync(outputPath, `${JSON.stringify(bundle)}\n`, "utf8");
console.log(`Problem bank bundle ready with ${manifest.problems.length} problems.`);
