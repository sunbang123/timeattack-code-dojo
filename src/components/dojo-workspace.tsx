"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import useSWR from "swr";

import { AnswerEditor } from "@/components/answer-editor";
import { AdminAuthControl } from "@/components/admin-auth-control";
import { CountdownTimer } from "@/components/countdown-timer";
import { DiscardDialog } from "@/components/discard-dialog";
import { ProblemGeneratorDialog } from "@/components/problem-generator-dialog";
import { ProblemPanel } from "@/components/problem-panel";
import { SelectionBar } from "@/components/selection-bar";
import { SubmissionFeedback } from "@/components/submission-feedback";
import { useAdminAuth } from "@/hooks/use-admin-auth";
import { useSolutionAccess } from "@/hooks/use-solution-access";
import {
  buildProblemUrl,
  fetchProblem,
  initialAnswer,
  submitAnswer,
  type ProblemPayload,
  type ProblemSelection,
  type SubmissionResult,
} from "@/lib/problem-api";
import {
  buildSolutionPath,
  writeSolutionAccess,
} from "@/lib/solution-access";

const defaultSelection: ProblemSelection = {
  mode: "intermediate",
  language: "python",
};

export function DojoWorkspace() {
  const [selection, setSelection] = useState<ProblemSelection>(defaultSelection);
  const [generatorOpen, setGeneratorOpen] = useState(false);
  const adminAuth = useAdminAuth();
  const requestUrl = buildProblemUrl(selection);
  const { data, error, isLoading, mutate } = useSWR(requestUrl, fetchProblem, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  const currentProblemId = data?.problem.id ?? selection.problemId ?? "";
  const hasLoadedWorkspace = Boolean(
    !isLoading && !error && data && data.available_problems.length > 0,
  );

  return (
    <main className="min-h-screen overflow-hidden bg-[#07091b] text-[#f4f1f8]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_72%_8%,rgba(102,247,255,0.12),transparent_26%),radial-gradient(circle_at_0%_82%,rgba(217,70,239,0.1),transparent_26%)]" />
      <div className="relative min-h-screen">
        <header className="flex flex-col gap-4 border-b border-[#66f7ff]/15 bg-[#07091b]/80 px-4 py-3 backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between md:px-6">
          <div className="flex items-center gap-3">
            <span className="relative size-12 shrink-0 overflow-hidden rounded-[14px] border border-[#66f7ff]/45 bg-[#0b1230] shadow-[0_0_26px_rgba(102,247,255,0.18)] sm:size-14">
              <Image
                alt="Timeattack Code Dojo"
                className="object-cover"
                fill
                priority
                sizes="56px"
                src="/timeattack-code-dojo-icon.png"
              />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <p className="font-mono text-xs font-semibold tracking-[0.16em] text-white/90">TIMEATTACK CODE DOJO</p>
                <span className="hidden rounded border border-[#d946ef]/30 bg-[#d946ef]/10 px-1.5 py-0.5 font-mono text-[8px] tracking-wider text-[#eda2ff] sm:inline">ARENA 01</span>
              </div>
              <p className="mt-1 text-[11px] text-white/42">제한 시간 안에, 끝까지 푼다.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <AdminAuthControl
              auth={adminAuth}
              onSignedOut={() => setGeneratorOpen(false)}
            />
            {data ? (
              <CountdownTimer
                key={`${data.problem.id}:${data.problem.version}:${data.problem.mode}:${data.problem.language}`}
                durationSeconds={data.problem.time_limit_seconds}
              />
            ) : null}
            <span className="hidden font-mono text-[10px] tracking-wider text-white/30 sm:inline">BANK V{data?.bank_version ?? "—"}</span>
            <span className="flex items-center gap-2 rounded-full border border-[#66f7ff]/20 bg-[#66f7ff]/5 px-3 py-1.5 font-mono text-[10px] tracking-wider text-[#98fbff]/70">
              <span className="size-1.5 animate-pulse rounded-full bg-[#66f7ff]" />
              LIVE · TRAINING
            </span>
          </div>
        </header>

        {isLoading ? (
          <>
            <SelectionBar
              availableProblems={data?.available_problems ?? []}
              currentProblemId={currentProblemId}
              disabled
              onAdd={adminAuth.isAdmin ? () => setGeneratorOpen(true) : undefined}
              onChange={setSelection}
              selection={selection}
            />
            <WorkspaceLoading />
          </>
        ) : error ? (
          <>
            <SelectionBar
              availableProblems={[]}
              currentProblemId=""
              onAdd={adminAuth.isAdmin ? () => setGeneratorOpen(true) : undefined}
              onChange={setSelection}
              selection={selection}
            />
            <WorkspaceError message={error instanceof Error ? error.message : "문제를 불러오지 못했습니다."} onRetry={() => void mutate()} />
          </>
        ) : !data || data.available_problems.length === 0 ? (
          <>
            <SelectionBar
              availableProblems={data?.available_problems ?? []}
              currentProblemId={currentProblemId}
              onAdd={adminAuth.isAdmin ? () => setGeneratorOpen(true) : undefined}
              onChange={setSelection}
              selection={selection}
            />
            <WorkspaceEmpty />
          </>
        ) : (
          <LoadedWorkspace
            key={`${data.problem.id}:${data.problem.version}:${data.problem.mode}:${data.problem.language}`}
            data={data}
            accessToken={adminAuth.accessToken}
            generatorOpen={generatorOpen}
            onAddProblem={adminAuth.isAdmin ? () => setGeneratorOpen(true) : undefined}
            onCloseGenerator={() => setGeneratorOpen(false)}
            onProblemBankChanged={() => void mutate()}
            onSelectionChange={setSelection}
            selection={selection}
          />
        )}
        {!hasLoadedWorkspace && adminAuth.accessToken ? (
          <ProblemGeneratorDialog
            accessToken={adminAuth.accessToken}
            onClose={() => setGeneratorOpen(false)}
            onCreated={(problem) => {
              setGeneratorOpen(false);
              setSelection((current) => ({ ...current, problemId: problem.id }));
            }}
            open={generatorOpen}
          />
        ) : null}
      </div>
    </main>
  );
}

function LoadedWorkspace({
  accessToken,
  data,
  generatorOpen,
  onAddProblem,
  onCloseGenerator,
  onProblemBankChanged,
  onSelectionChange,
  selection,
}: {
  accessToken: string | null;
  data: import("@/lib/problem-api").ProblemResponse;
  generatorOpen: boolean;
  onAddProblem?: () => void;
  onCloseGenerator: () => void;
  onProblemBankChanged: () => void;
  onSelectionChange: (selection: ProblemSelection) => void;
  selection: ProblemSelection;
}) {
  const router = useRouter();
  const startingAnswer = initialAnswer(data.problem);
  const [answer, setAnswer] = useState(startingAnswer);
  const [lastSubmittedAnswer, setLastSubmittedAnswer] = useState(startingAnswer);
  const [pendingSelection, setPendingSelection] = useState<ProblemSelection | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<SubmissionResult | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const { access: solutionAccess } = useSolutionAccess(data.problem);
  const wrongAttemptCount = solutionAccess?.wrongAttempts ?? 0;
  const solutionAccessToken = solutionAccess?.token ?? null;
  const isDirty = answer !== lastSubmittedAnswer;

  useEffect(() => {
    if (!isDirty) return;
    const warnBeforeLeaving = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeLeaving);
    return () => window.removeEventListener("beforeunload", warnBeforeLeaving);
  }, [isDirty]);

  const applySelection = useCallback(
    (nextSelection: ProblemSelection) => {
      setPendingSelection(null);
      onSelectionChange(nextSelection);
    },
    [onSelectionChange],
  );

  const requestSelection = useCallback(
    (nextSelection: ProblemSelection) => {
      if (JSON.stringify(nextSelection) === JSON.stringify(selection)) return;
      if (isDirty) {
        setPendingSelection(nextSelection);
        return;
      }
      applySelection(nextSelection);
    },
    [applySelection, isDirty, selection],
  );

  const cancelSelection = useCallback(() => setPendingSelection(null), []);
  const confirmSelection = useCallback(() => {
    if (pendingSelection) applySelection(pendingSelection);
  }, [applySelection, pendingSelection]);

  const handleAnswerChange = useCallback((value: string) => {
    setAnswer(value);
    setSubmissionResult(null);
    setSubmissionError(null);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!answer.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setSubmissionError(null);
    try {
      const result = await submitAnswer(data.problem, answer);
      setSubmissionResult(result);
      setLastSubmittedAnswer(answer);
      if (!result.passed && result.solution_access_token) {
        writeSolutionAccess(data.problem, {
          token: result.solution_access_token,
          wrongAttempts: wrongAttemptCount + 1,
        });
      }
    } catch (error) {
      setSubmissionResult(null);
      setSubmissionError(error instanceof Error ? error.message : "답안을 제출하지 못했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }, [answer, data.problem, isSubmitting, wrongAttemptCount]);

  const handleViewSolution = useCallback(() => {
    if (wrongAttemptCount < 1 || !solutionAccessToken) return;
    writeSolutionAccess(data.problem, {
      token: solutionAccessToken,
      wrongAttempts: wrongAttemptCount,
    });
    router.push(buildSolutionPath(data.problem));
  }, [data.problem, router, solutionAccessToken, wrongAttemptCount]);

  return (
    <>
      <SelectionBar
        availableProblems={data.available_problems}
        currentProblemId={data.problem.id}
        onAdd={onAddProblem}
        onChange={requestSelection}
        selection={selection}
      />
      <div className="grid min-h-[calc(100vh-188px)] border-b border-white/10 lg:h-[calc(100vh-188px)] lg:grid-cols-[0.88fr_1.12fr]">
        <div className="min-h-[34rem] overflow-hidden border-b border-white/10 lg:min-h-0 lg:border-b-0 lg:border-r">
          <ProblemPanel problem={data.problem} />
        </div>
        <section className="flex min-h-[38rem] flex-col bg-[#080c1d] lg:min-h-0" aria-label="답안 작성">
          <EditorHeader isDirty={isDirty} problem={data.problem} />
          <div className="min-h-0 flex-1 overflow-hidden">
            <AnswerEditor onChange={handleAnswerChange} problem={data.problem} value={answer} />
          </div>
          <SubmissionFeedback error={submissionError} result={submissionResult} />
          <EditorFooter
            isDirty={isDirty}
            isSubmitting={isSubmitting}
            onViewSolution={handleViewSolution}
            onSubmit={() => void handleSubmit()}
            solutionAvailable={wrongAttemptCount >= 1 && solutionAccessToken !== null}
            value={answer}
            wrongAttemptCount={wrongAttemptCount}
          />
        </section>
      </div>
      <DiscardDialog
        onCancel={cancelSelection}
        onConfirm={confirmSelection}
        open={pendingSelection !== null}
      />
      {accessToken ? (
        <ProblemGeneratorDialog
          accessToken={accessToken}
          onClose={onCloseGenerator}
          onCreated={(problem) => {
            onCloseGenerator();
            onProblemBankChanged();
            requestSelection({ ...selection, problemId: problem.id });
          }}
          open={generatorOpen}
        />
      ) : null}
    </>
  );
}

function EditorHeader({
  isDirty,
  problem,
}: {
  isDirty: boolean;
  problem: ProblemPayload;
}) {
  const minutes = problem.time_limit_seconds / 60;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3 md:px-5">
      <div className="flex items-center gap-2 font-mono text-[10px] tracking-wider text-white/35">
        <span className="text-[#66f7ff]">{problem.language === "python" ? "PY" : "CPP"}</span>
        <span>/</span>
        <span>{problem.mode.toUpperCase()}</span>
        <span>/</span>
        <span>{minutes} MIN</span>
      </div>
      <span aria-live="polite" className={`flex items-center gap-2 text-xs ${isDirty ? "text-[#ffad96]" : "text-white/35"}`}>
        <span className={`size-1.5 rounded-full ${isDirty ? "bg-[#ff7a59]" : "bg-white/25"}`} />
        {isDirty ? "작성 중 · 미제출" : "초기 답안"}
      </span>
    </div>
  );
}

function EditorFooter({
  isDirty,
  isSubmitting,
  onViewSolution,
  onSubmit,
  solutionAvailable,
  value,
  wrongAttemptCount,
}: {
  isDirty: boolean;
  isSubmitting: boolean;
  onViewSolution: () => void;
  onSubmit: () => void;
  solutionAvailable: boolean;
  value: string;
  wrongAttemptCount: number;
}) {
  const lineCount = value === "" ? 1 : value.split("\n").length;
  const disabled = isSubmitting || !value.trim();
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 px-4 py-3 md:px-5">
      <div className="flex gap-4 font-mono text-[10px] text-white/30">
        <span>{lineCount} LINES</span>
        <span>{value.length} CHARS</span>
        <span>{isDirty ? "UNSAVED" : "READY"}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          className="rounded-lg border border-white/12 bg-white/[0.035] px-4 py-2 text-xs font-semibold text-white/65 transition hover:border-[#ff7a59]/45 hover:text-[#ffad96] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff7a59]/50 disabled:cursor-not-allowed disabled:border-white/6 disabled:bg-transparent disabled:text-white/20"
          disabled={!solutionAvailable}
          onClick={onViewSolution}
          title={solutionAvailable ? "풀이과정 페이지로 이동" : "오답 제출 후 확인할 수 있습니다."}
          type="button"
        >
          {solutionAvailable ? `정답보기 · 오답 ${wrongAttemptCount}회` : "정답보기 · 1회 오답 후"}
        </button>
        <button
          className="rounded-lg bg-[#66f7ff] px-4 py-2 text-xs font-semibold text-[#031316] shadow-[0_0_24px_rgba(102,247,255,0.12)] transition hover:bg-[#9ffaff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b9fdff] disabled:cursor-not-allowed disabled:bg-white/[0.04] disabled:text-white/25"
          disabled={disabled}
          onClick={onSubmit}
          type="button"
        >
          {isSubmitting ? "채점 중…" : "답안 제출"}
        </button>
      </div>
    </div>
  );
}

function WorkspaceLoading() {
  return (
    <div className="grid min-h-[calc(100vh-188px)] animate-pulse gap-px bg-white/8 lg:grid-cols-[0.88fr_1.12fr]" aria-live="polite" aria-label="문제 불러오는 중">
      <div className="bg-[#0c1216] p-7">
        <div className="h-3 w-32 rounded bg-white/8" />
        <div className="mt-8 h-10 w-2/3 rounded bg-white/8" />
        <div className="mt-5 h-3 w-full rounded bg-white/5" />
        <div className="mt-3 h-3 w-4/5 rounded bg-white/5" />
      </div>
      <div className="grid place-items-center bg-[#080c1d] font-mono text-xs text-white/30">LOADING PROBLEM DATA</div>
    </div>
  );
}

function WorkspaceError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="grid min-h-[calc(100vh-188px)] place-items-center px-5 py-16 text-center" aria-live="assertive">
      <div className="max-w-md">
        <span className="mx-auto grid size-12 place-items-center rounded-full border border-[#ff7a59]/30 bg-[#ff7a59]/10 font-mono text-[#ff9b80]">!</span>
        <h1 className="mt-5 text-2xl font-semibold">문제를 불러오지 못했어요</h1>
        <p className="mt-2 text-sm leading-6 text-white/45">{message}</p>
        <button className="mt-6 rounded-lg bg-[#66f7ff] px-5 py-3 text-sm font-semibold text-[#031316] transition hover:bg-[#9ffaff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b9fdff]" onClick={onRetry} type="button">
          다시 시도
        </button>
      </div>
    </section>
  );
}

function WorkspaceEmpty() {
  return (
    <section className="grid min-h-[calc(100vh-188px)] place-items-center px-5 py-16 text-center">
      <div>
        <p className="font-mono text-xs tracking-[0.2em] text-white/30">EMPTY PROBLEM BANK</p>
        <h1 className="mt-4 text-2xl font-semibold">문제은행에 준비된 문제가 없습니다.</h1>
        <p className="mt-2 text-sm text-white/40">잠시 후 다시 시도해 주세요.</p>
      </div>
    </section>
  );
}
