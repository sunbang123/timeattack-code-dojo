import { cpSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";

const projectRoot = process.cwd();
const source = path.join(projectRoot, "node_modules", "monaco-editor", "min", "vs");
const destination = path.join(projectRoot, "public", "monaco", "vs");

if (!existsSync(source)) {
  throw new Error("monaco-editor assets are missing. Run `pnpm install` first.");
}

mkdirSync(destination, { recursive: true });
cpSync(source, destination, { recursive: true, force: true });
console.log("Monaco assets ready at public/monaco/vs");
