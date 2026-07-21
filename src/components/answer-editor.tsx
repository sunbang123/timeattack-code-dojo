"use client";

import { CodeEditor } from "@/components/code-editor";
import { useMediaQuery } from "@/hooks/use-media-query";
import type { ProblemPayload } from "@/lib/problem-api";

type AnswerEditorProps = {
  problem: ProblemPayload;
  value: string;
  onChange: (value: string) => void;
};

export function AnswerEditor({ problem, value, onChange }: AnswerEditorProps) {
  const isCompact = useMediaQuery("(max-width: 767px)");
  const isPseudocode = problem.mode === "beginner";

  if (isPseudocode) {
    return (
      <textarea
        aria-label="의사코드 답안"
        className="h-full min-h-96 w-full resize-none bg-[#090e12] p-5 font-mono text-sm leading-7 text-[#e9e6dd] outline-none placeholder:text-white/25 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#2cffad]/70"
        onChange={(event) => onChange(event.target.value)}
        placeholder="예: 두 정수를 읽는다 → 두 값을 더한다 → 결과를 출력한다"
        spellCheck={false}
        value={value}
      />
    );
  }

  if (isCompact === null) {
    return <div className="h-full min-h-96 animate-pulse bg-white/[0.03]" aria-label="편집기 준비 중" />;
  }

  if (isCompact) {
    return (
      <textarea
        aria-label={`${problem.language === "python" ? "Python" : "C++"} 코드 답안`}
        className="h-full min-h-[32rem] w-full resize-y bg-[#090e12] p-5 font-mono text-[13px] leading-6 text-[#e9e6dd] outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#2cffad]/70"
        onChange={(event) => onChange(event.target.value)}
        spellCheck={false}
        value={value}
      />
    );
  }

  const extension = problem.language === "python" ? "py" : "cpp";
  return (
    <CodeEditor
      language={problem.language}
      onChange={onChange}
      path={`${problem.id}-${problem.mode}.${extension}`}
      value={value}
    />
  );
}
