"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";

import { useSolutionAccess } from "@/hooks/use-solution-access";
import {
  fetchSolution,
  type SolutionPayload,
} from "@/lib/problem-api";
import type { SolutionScope } from "@/lib/solution-access";

const modeLabels: Record<SolutionScope["mode"], string> = {
  beginner: "초보 · 의사코드",
  intermediate: "중수 · TODO 구현",
  expert: "고수 · 처음부터 구현",
};

export function SolutionWorkspace({ scope }: { scope: SolutionScope }) {
  const { access, isBrowser } = useSolutionAccess(scope);
  const accessToken = access?.token ?? null;
  const [loadState, setLoadState] = useState<SolutionLoadState | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    void fetchSolution(scope, accessToken)
      .then((payload) => {
        if (active) {
          setLoadState({ status: "loaded", token: accessToken, solution: payload });
        }
      })
      .catch((fetchError: unknown) => {
        if (active) {
          setLoadState({
            status: "error",
            token: accessToken,
            message: fetchError instanceof Error ? fetchError.message : "풀이를 불러오지 못했습니다.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [accessToken, scope]);

  if (!isBrowser) {
    return <SolutionLoading />;
  }

  if (!accessToken) {
    return <SolutionError message="이 문제와 학습 모드에서 오답을 한 번 제출한 뒤 정답보기 버튼을 눌러 주세요." />;
  }

  if (!loadState || loadState.token !== accessToken) {
    return <SolutionLoading />;
  }

  if (loadState.status === "error") {
    return <SolutionError message={loadState.message} />;
  }

  const solution = loadState.solution;

  return (
    <main className="min-h-screen bg-[#07091b] text-[#f4f1f8]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_80%_0%,rgba(102,247,255,0.12),transparent_28%),radial-gradient(circle_at_0%_90%,rgba(217,70,239,0.1),transparent_24%)]" />
      <div className="relative mx-auto max-w-5xl px-5 py-8 md:px-8 md:py-12">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div className="flex items-center gap-3">
            <span className="relative size-12 overflow-hidden rounded-[14px] border border-[#66f7ff]/40 shadow-[0_0_24px_rgba(102,247,255,0.16)]">
              <Image alt="Timeattack Code Dojo" className="object-cover" fill sizes="48px" src="/timeattack-code-dojo-icon.png" />
            </span>
            <div>
              <p className="font-mono text-[10px] tracking-[0.2em] text-[#66f7ff]">SOLUTION WALKTHROUGH</p>
              <p className="mt-2 text-xs text-white/40">
                {modeLabels[solution.mode]} · {solution.language === "python" ? "Python" : "C++"}
              </p>
            </div>
          </div>
          <Link
            className="rounded-lg border border-white/12 bg-white/[0.035] px-4 py-2.5 text-xs font-semibold text-white/65 transition hover:border-white/25 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#66f7ff]/60"
            href="/"
          >
            ← 문제로 돌아가기
          </Link>
        </header>

        <article className="py-9 md:py-12">
          <p className="font-mono text-[10px] tracking-[0.16em] text-white/30">
            {solution.problem_id} · V{solution.version}
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] md:text-5xl">{solution.title}</h1>
          <p className="mt-5 max-w-3xl text-base leading-7 text-white/55">{solution.summary}</p>

          <section className="mt-10 rounded-2xl border border-white/9 bg-[#0c1216] p-5 md:p-7">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">풀이 과정</h2>
              <span className="font-mono text-[10px] text-white/30">{solution.steps.length} STEPS</span>
            </div>
            <ol className="mt-6 grid gap-5">
              {solution.steps.map((step, index) => (
                <li className="grid grid-cols-[2rem_1fr] gap-3" key={`${index}-${step}`}>
                  <span className="grid size-8 place-items-center rounded-full border border-[#66f7ff]/25 bg-[#66f7ff]/8 font-mono text-xs text-[#98fbff]">
                    {index + 1}
                  </span>
                  <p className="pt-1 text-sm leading-6 text-white/62">{step}</p>
                </li>
              ))}
            </ol>
          </section>

          <section className="mt-6 overflow-hidden rounded-2xl border border-white/9 bg-[#080c1d]">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/9 px-5 py-4 md:px-7">
              <div>
                <h2 className="text-sm font-semibold">정답 코드</h2>
                <p className="mt-1 text-xs text-white/35">풀이 단계를 이해한 뒤 자신의 답안과 비교해 보세요.</p>
              </div>
              <span className="rounded border border-white/10 px-2 py-1 font-mono text-[10px] text-white/45">
                {solution.language === "python" ? "PYTHON" : "C++"}
              </span>
            </div>
            <pre className="max-h-[38rem] overflow-y-auto whitespace-pre-wrap break-words p-5 font-mono text-xs leading-6 text-white/72 [tab-size:2] md:p-7">
              <code>{solution.reference_solution.trimEnd()}</code>
            </pre>
          </section>
        </article>
      </div>
    </main>
  );
}

type SolutionLoadState =
  | { status: "loaded"; token: string; solution: SolutionPayload }
  | { status: "error"; token: string; message: string };

function SolutionLoading() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#070b0f] px-5 text-[#f4f1e8]" aria-live="polite">
      <div className="text-center">
        <span className="mx-auto block size-7 animate-spin rounded-full border-2 border-white/15 border-t-[#66f7ff]" />
        <p className="mt-4 font-mono text-xs tracking-[0.18em] text-white/40">LOADING WALKTHROUGH</p>
      </div>
    </main>
  );
}

function SolutionError({ message }: { message: string }) {
  return (
    <main className="grid min-h-screen place-items-center bg-[#070b0f] px-5 text-center text-[#f4f1e8]" aria-live="assertive">
      <div className="max-w-lg">
        <span className="mx-auto grid size-12 place-items-center rounded-full border border-[#ff7a59]/30 bg-[#ff7a59]/10 font-mono text-[#ff9b80]">!</span>
        <h1 className="mt-5 text-2xl font-semibold">아직 풀이를 열 수 없어요</h1>
        <p className="mt-3 text-sm leading-6 text-white/50">{message}</p>
        <Link className="mt-7 inline-flex rounded-lg bg-[#66f7ff] px-5 py-3 text-sm font-semibold text-[#031316]" href="/">
          문제로 돌아가기
        </Link>
      </div>
    </main>
  );
}
