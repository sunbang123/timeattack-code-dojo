export const DIFFICULTIES = ["easy", "medium", "hard"] as const;
export const MODES = ["beginner", "intermediate", "expert"] as const;
export const LANGUAGES = ["python", "cpp"] as const;

export type Difficulty = (typeof DIFFICULTIES)[number];
export type Mode = (typeof MODES)[number];
export type Language = (typeof LANGUAGES)[number];

export type ProblemSelection = {
  difficulty: Difficulty;
  mode: Mode;
  language: Language;
  problemId?: string;
};

export type ProblemSummary = {
  id: string;
  title: string;
  difficulty: Difficulty;
};

export type ProblemExample = {
  input: string;
  output: string;
  explanation: string;
};

export type ProblemPayload = {
  id: string;
  version: number;
  title: string;
  difficulty: Difficulty;
  tags: string[];
  statement: {
    summary: string;
    description: string;
    input: string;
    output: string;
    constraints: string[];
  };
  examples: ProblemExample[];
  mode: Mode;
  language: Language;
  time_limit_seconds: number;
  answer_format: "pseudocode" | "code";
  prompt?: string;
  starter_code?: string;
};

export type ProblemResponse = {
  available_problems: ProblemSummary[];
  bank_version: number;
  problem: ProblemPayload;
};

export type SubmissionResult = {
  kind: "code" | "pseudocode";
  status: "accepted" | "wrong_answer" | "compile_error" | "runtime_error" | "evaluated";
  passed: boolean;
  score: number;
  feedback: string;
  passed_tests?: number;
  total_tests?: number;
  detail?: string;
  missing_steps?: string[];
};

type ErrorResponse = {
  error?: {
    message?: string;
  };
};

export class ProblemApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ProblemApiError";
  }
}

export function buildProblemUrl(selection: ProblemSelection): string {
  const parameters = new URLSearchParams({
    difficulty: selection.difficulty,
    mode: selection.mode,
    language: selection.language,
  });
  if (selection.problemId) {
    parameters.set("problem_id", selection.problemId);
  }
  return `/api/problem?${parameters.toString()}`;
}

export async function fetchProblem(url: string): Promise<ProblemResponse> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    let message = `문제를 불러오지 못했습니다. (HTTP ${response.status})`;
    try {
      const payload = (await response.json()) as ErrorResponse;
      if (payload.error?.message) {
        message = payload.error.message;
      }
    } catch {
      // Keep the safe fallback message when the response is not JSON.
    }
    throw new ProblemApiError(message, response.status);
  }
  return (await response.json()) as ProblemResponse;
}

export async function submitAnswer(
  problem: ProblemPayload,
  answer: string,
): Promise<SubmissionResult> {
  const response = await fetch("/api/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      problem_id: problem.id,
      version: problem.version,
      mode: problem.mode,
      language: problem.language,
      answer,
    }),
  });
  const payload = (await response.json()) as ErrorResponse & { result?: SubmissionResult };
  if (!response.ok || !payload.result) {
    throw new ProblemApiError(
      payload.error?.message ?? `답안을 제출하지 못했습니다. (HTTP ${response.status})`,
      response.status,
    );
  }
  return payload.result;
}

export function initialAnswer(problem: ProblemPayload): string {
  if (problem.mode === "beginner") {
    return "";
  }
  return problem.starter_code ?? "";
}
