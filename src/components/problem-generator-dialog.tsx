"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  generateProblem,
  type Difficulty,
  type ProblemSummary,
} from "@/lib/problem-api";

type ProblemGeneratorDialogProps = {
  open: boolean;
  onClose: () => void;
  onCreated: (problem: ProblemSummary) => void;
};

const difficultyOptions: { value: Difficulty; label: string; caption: string }[] = [
  { value: "easy", label: "쉬움", caption: "기초 구현" },
  { value: "medium", label: "보통", caption: "자료구조·응용" },
  { value: "hard", label: "어려움", caption: "고급 알고리즘" },
];

export function ProblemGeneratorDialog({
  open,
  onClose,
  onCreated,
}: ProblemGeneratorDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [prompt, setPrompt] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    if (isGenerating) return;
    setError(null);
    onClose();
  };

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (prompt.trim().length < 10 || isGenerating) return;
    setIsGenerating(true);
    setError(null);
    try {
      const result = await generateProblem(prompt.trim(), difficulty);
      setPrompt("");
      onCreated(result.problem);
    } catch (generationError) {
      setError(
        generationError instanceof Error
          ? generationError.message
          : "문제를 생성하지 못했습니다.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="m-auto w-[calc(100%-2rem)] max-w-xl rounded-2xl border border-white/12 bg-[#10171c] p-0 text-[#f4f1e8] shadow-2xl shadow-black/60 backdrop:bg-black/75 backdrop:backdrop-blur-sm"
      onCancel={(event) => {
        event.preventDefault();
        handleClose();
      }}
    >
      <form aria-labelledby="generator-title" onSubmit={handleSubmit}>
        <div className="border-b border-white/10 px-5 py-5 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[9px] tracking-[0.2em] text-[#2cffad]">
                HUGGING FACE · AI AUTHOR
              </p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight" id="generator-title">
                새 문제 만들기
              </h2>
              <p className="mt-1.5 text-xs leading-5 text-white/45">
                주제와 원하는 조건을 적으면 문제·예제·채점 데이터를 함께 생성합니다.
              </p>
            </div>
            <button
              aria-label="문제 생성 창 닫기"
              className="grid size-8 shrink-0 place-items-center rounded-lg border border-white/10 text-white/40 transition hover:bg-white/5 hover:text-white disabled:opacity-30"
              disabled={isGenerating}
              onClick={handleClose}
              type="button"
            >
              ×
            </button>
          </div>
        </div>

        <div className="space-y-5 px-5 py-5 sm:px-6">
          <label className="block">
            <span className="font-mono text-[10px] tracking-[0.16em] text-white/45">
              문제 요청
            </span>
            <textarea
              autoFocus
              className="mt-2 min-h-32 w-full resize-y rounded-xl border border-white/10 bg-[#090e12] px-4 py-3 text-sm leading-6 text-white/80 outline-none transition placeholder:text-white/20 focus:border-[#2cffad]/45 focus:ring-2 focus:ring-[#2cffad]/15"
              disabled={isGenerating}
              maxLength={2000}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="예: 투 포인터를 연습할 수 있는 문자열 문제. 입력 크기는 100,000 이하이고 예외 케이스가 분명했으면 좋겠어요."
              required
              value={prompt}
            />
            <span className="mt-1.5 block text-right font-mono text-[9px] text-white/25">
              {prompt.length} / 2000
            </span>
          </label>

          <fieldset disabled={isGenerating}>
            <legend className="font-mono text-[10px] tracking-[0.16em] text-white/45">
              난이도
            </legend>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {difficultyOptions.map((option) => {
                const active = difficulty === option.value;
                return (
                  <button
                    key={option.value}
                    aria-pressed={active}
                    className={`rounded-xl border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2cffad]/60 ${
                      active
                        ? "border-[#2cffad]/45 bg-[#2cffad]/9 text-[#8affd5]"
                        : "border-white/8 bg-white/[0.025] text-white/45 hover:border-white/20"
                    }`}
                    onClick={() => setDifficulty(option.value)}
                    type="button"
                  >
                    <span className="block text-xs font-semibold">{option.label}</span>
                    <span className="mt-1 block text-[9px] opacity-55">{option.caption}</span>
                  </button>
                );
              })}
            </div>
          </fieldset>

          {error ? (
            <p className="rounded-lg border border-[#ff7a59]/25 bg-[#ff7a59]/8 px-3 py-2.5 text-xs leading-5 text-[#ffad96]" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-white/10 px-5 py-4 sm:px-6">
          <p className="hidden text-[10px] text-white/30 sm:block">
            생성에는 최대 1분 정도 걸릴 수 있어요.
          </p>
          <div className="ml-auto flex gap-2">
            <button
              className="rounded-lg border border-white/12 px-4 py-2.5 text-xs text-white/60 transition hover:bg-white/5 hover:text-white disabled:opacity-30"
              disabled={isGenerating}
              onClick={handleClose}
              type="button"
            >
              취소
            </button>
            <button
              className="min-w-28 rounded-lg bg-[#2cffad] px-4 py-2.5 text-xs font-semibold text-[#03140e] transition hover:bg-[#72ffcf] disabled:cursor-not-allowed disabled:bg-white/[0.06] disabled:text-white/25"
              disabled={isGenerating || prompt.trim().length < 10}
              type="submit"
            >
              {isGenerating ? "문제 생성 중…" : "AI로 생성"}
            </button>
          </div>
        </div>
      </form>
    </dialog>
  );
}
