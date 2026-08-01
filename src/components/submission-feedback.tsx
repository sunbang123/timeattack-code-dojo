import type { SubmissionResult } from "@/lib/problem-api";

type SubmissionFeedbackProps = {
  error: string | null;
  result: SubmissionResult | null;
};

export function SubmissionFeedback({ error, result }: SubmissionFeedbackProps) {
  if (!error && !result) return null;

  const passed = result?.passed ?? false;
  return (
    <aside
      aria-live="polite"
      className={`border-t px-4 py-3 md:px-5 ${
        passed
          ? "border-[#66f7ff]/20 bg-[#66f7ff]/[0.055]"
          : "border-[#ff7a59]/20 bg-[#ff7a59]/[0.055]"
      }`}
    >
      {error ? (
        <p className="text-sm text-[#ffad96]">{error}</p>
      ) : result ? (
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className={`text-sm font-semibold ${passed ? "text-[#98fbff]" : "text-[#ffad96]"}`}>
              {passed ? "통과했습니다" : "조금 더 다듬어 보세요"}
            </p>
            <p className="mt-1 text-xs leading-5 text-white/55">{result.feedback}</p>
            {result.detail && (
              <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-white/45">
                {result.detail}
              </pre>
            )}
            {result.missing_steps && result.missing_steps.length > 0 && (
              <p className="mt-2 text-xs text-white/45">
                보완할 점: {result.missing_steps.join(" · ")}
              </p>
            )}
          </div>
          <div className="flex gap-2 font-mono text-[10px] text-white/45">
            <span className="rounded border border-white/10 px-2 py-1">SCORE {result.score}</span>
            {result.total_tests !== undefined && (
              <span className="rounded border border-white/10 px-2 py-1">
                TEST {result.passed_tests}/{result.total_tests}
              </span>
            )}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
