import type { ProblemPayload } from "@/lib/problem-api";

export type SolutionScope = Pick<ProblemPayload, "id" | "version" | "mode" | "language">;

export type StoredSolutionAccess = {
  token: string;
  wrongAttempts: number;
};

export const SOLUTION_ACCESS_EVENT = "timeattack:solution-access";

export function solutionAccessKey(scope: SolutionScope): string {
  return [
    "solution-access",
    scope.id,
    scope.version,
    scope.mode,
    scope.language,
  ].join(":");
}

export function parseSolutionAccess(raw: string | null): StoredSolutionAccess | null {
  if (!raw) return null;

  try {
    const value = JSON.parse(raw) as Partial<StoredSolutionAccess>;
    if (
      typeof value.token !== "string" ||
      value.token.length === 0 ||
      typeof value.wrongAttempts !== "number" ||
      !Number.isInteger(value.wrongAttempts) ||
      value.wrongAttempts < 1
    ) {
      return null;
    }
    return { token: value.token, wrongAttempts: value.wrongAttempts };
  } catch {
    return null;
  }
}

export function writeSolutionAccess(
  scope: SolutionScope,
  value: StoredSolutionAccess,
): void {
  if (typeof window === "undefined") return;
  const key = solutionAccessKey(scope);
  window.sessionStorage.setItem(key, JSON.stringify(value));
  window.dispatchEvent(new CustomEvent(SOLUTION_ACCESS_EVENT, { detail: key }));
}

export function buildSolutionPath(scope: SolutionScope): string {
  const parameters = new URLSearchParams({
    version: String(scope.version),
    mode: scope.mode,
    language: scope.language,
  });
  return `/solutions/${encodeURIComponent(scope.id)}?${parameters.toString()}`;
}
