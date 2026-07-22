"use client";

import type {
  Language,
  Mode,
  ProblemSelection,
  ProblemSummary,
} from "@/lib/problem-api";

const modeOptions: { value: Mode; label: string; caption: string }[] = [
  { value: "beginner", label: "초보", caption: "의사코드" },
  { value: "intermediate", label: "중수", caption: "TODO 구현" },
  { value: "expert", label: "고수", caption: "처음부터" },
];

const languageOptions: { value: Language; label: string }[] = [
  { value: "python", label: "Python" },
  { value: "cpp", label: "C++" },
];

const difficultyLabels: Record<ProblemSummary["difficulty"], string> = {
  easy: "쉬움",
  medium: "보통",
  hard: "어려움",
};

const segmentClass =
  "rounded-lg border px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2cffad]/70";

type SelectionBarProps = {
  availableProblems: ProblemSummary[];
  currentProblemId: string;
  disabled?: boolean;
  selection: ProblemSelection;
  onAdd: () => void;
  onChange: (selection: ProblemSelection) => void;
};

export function SelectionBar({
  availableProblems,
  currentProblemId,
  disabled = false,
  selection,
  onAdd,
  onChange,
}: SelectionBarProps) {
  return (
    <section
      aria-label="문제 설정"
      className="grid gap-5 border-b border-white/10 bg-[#0a0f13]/95 px-4 py-4 backdrop-blur md:grid-cols-[minmax(0,1.35fr)_1.35fr_0.75fr] md:px-6"
    >
      <div>
        <div className="mb-2 flex items-center justify-between font-mono text-[10px] tracking-[0.18em] text-white/35">
          <span>ALL PROBLEMS</span>
          <span className="flex items-center gap-3">
            <span>{availableProblems.length}개</span>
            <button
              className="rounded border border-[#2cffad]/25 bg-[#2cffad]/7 px-2 py-1 text-[9px] tracking-[0.1em] text-[#7dffcc] transition hover:border-[#2cffad]/50 hover:bg-[#2cffad]/12 disabled:cursor-not-allowed disabled:opacity-30"
              disabled={disabled}
              onClick={onAdd}
              type="button"
            >
              + 문제 추가
            </button>
          </span>
        </div>
        <label>
          <span className="sr-only">문제 선택</span>
          <select
            className="h-[58px] w-full rounded-lg border border-white/10 bg-[#10171c] px-3 text-sm text-white/80 outline-none transition focus:border-[#2cffad]/50 focus:ring-2 focus:ring-[#2cffad]/20 disabled:opacity-50"
            disabled={disabled || availableProblems.length === 0}
            onChange={(event) =>
              onChange({ ...selection, problemId: event.target.value })
            }
            value={currentProblemId}
          >
            {availableProblems.map((problem) => (
              <option key={problem.id} value={problem.id}>
                [{difficultyLabels[problem.difficulty]}] {problem.title}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset disabled={disabled}>
        <legend className="mb-2 font-mono text-[10px] tracking-[0.18em] text-white/35">TRAINING MODE</legend>
        <div className="grid grid-cols-3 gap-1.5">
          {modeOptions.map((option) => {
            const active = selection.mode === option.value;
            return (
              <button
                key={option.value}
                aria-pressed={active}
                className={`${segmentClass} ${
                  active
                    ? "border-[#2cffad]/50 bg-[#2cffad]/10 text-[#7dffcc]"
                    : "border-white/8 bg-white/[0.025] text-white/45 hover:border-white/20 hover:text-white/75"
                }`}
                onClick={() =>
                  onChange({ ...selection, mode: option.value, problemId: currentProblemId })
                }
                type="button"
              >
                <span className="block text-xs font-medium">{option.label}</span>
                <span className="mt-0.5 block text-[9px] opacity-55">{option.caption}</span>
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend className="mb-2 font-mono text-[10px] tracking-[0.18em] text-white/35">LANGUAGE</legend>
        <div className="grid grid-cols-2 gap-1.5">
          {languageOptions.map((option) => {
            const active = selection.language === option.value;
            return (
              <button
                key={option.value}
                aria-pressed={active}
                className={`${segmentClass} h-[58px] text-center font-mono text-xs ${
                  active
                    ? "border-white/25 bg-white/10 text-white"
                    : "border-white/8 bg-white/[0.025] text-white/40 hover:border-white/20 hover:text-white/70"
                }`}
                onClick={() =>
                  onChange({ ...selection, language: option.value, problemId: currentProblemId })
                }
                type="button"
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </fieldset>
    </section>
  );
}
