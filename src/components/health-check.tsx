"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type HealthPayload = {
  environment: string;
  runtime: string;
  service: string;
  status: "ok";
  version: string;
};

type HealthState =
  | { kind: "checking" }
  | { kind: "ready"; payload: HealthPayload }
  | { kind: "error"; message: string };

export function HealthCheck() {
  const [state, setState] = useState<HealthState>({ kind: "checking" });
  const activeController = useRef<AbortController | null>(null);
  const activeTimeout = useRef<number | null>(null);

  const checkHealth = useCallback(async () => {
    activeController.current?.abort();
    if (activeTimeout.current !== null) {
      window.clearTimeout(activeTimeout.current);
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 5_000);
    activeController.current = controller;
    activeTimeout.current = timeout;

    try {
      const response = await fetch("/api/health", {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`API가 HTTP ${response.status}를 반환했습니다.`);
      }
      const payload = (await response.json()) as HealthPayload;
      if (payload.status !== "ok") {
        throw new Error("API 상태 응답이 올바르지 않습니다.");
      }
      setState({ kind: "ready", payload });
    } catch (error) {
      setState({
        kind: "error",
        message: error instanceof Error ? error.message : "API 연결에 실패했습니다.",
      });
    } finally {
      window.clearTimeout(timeout);
      if (activeController.current === controller) {
        activeController.current = null;
        activeTimeout.current = null;
      }
    }
  }, []);

  useEffect(() => {
    const startRequest = window.setTimeout(() => void checkHealth(), 0);
    return () => {
      window.clearTimeout(startRequest);
      activeController.current?.abort();
      if (activeTimeout.current !== null) {
        window.clearTimeout(activeTimeout.current);
      }
    };
  }, [checkHealth]);

  const isReady = state.kind === "ready";

  return (
    <aside className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0b1015] p-6">
      <div className="absolute -right-16 -top-16 size-44 rounded-full bg-[#2cffad]/8 blur-3xl" />
      <div className="relative">
        <div className="mb-12 flex items-center justify-between">
          <span className="font-mono text-xs tracking-[0.2em] text-white/40">SYSTEM CHECK</span>
          <span
            className={`size-2.5 rounded-full ${
              isReady
                ? "bg-[#2cffad] shadow-[0_0_18px_rgba(44,255,173,0.8)]"
                : state.kind === "error"
                  ? "bg-[#ff5b34]"
                  : "animate-pulse bg-amber-300"
            }`}
          />
        </div>

        <p className="mb-2 text-sm text-white/45">Frontend ↔ API</p>
        <h2 aria-live="polite" className="text-3xl font-medium tracking-tight">
          {isReady ? "연결 완료" : state.kind === "checking" ? "확인 중…" : "연결 필요"}
        </h2>

        <div className="mt-8 rounded-xl border border-white/8 bg-black/20 p-4 font-mono text-xs leading-6 text-white/50">
          {state.kind === "ready" ? (
            <>
              <p><span className="text-[#2cffad]">GET</span> /api/health · 200</p>
              <p>{state.payload.service} · v{state.payload.version}</p>
              <p>{state.payload.runtime} · {state.payload.environment}</p>
            </>
          ) : state.kind === "error" ? (
            <p className="text-[#ff8e72]">{state.message}</p>
          ) : (
            <p>Flask 런타임을 깨우고 있습니다.</p>
          )}
        </div>

        {state.kind === "error" && (
          <button
            type="button"
            onClick={() => {
              setState({ kind: "checking" });
              void checkHealth();
            }}
            className="mt-4 rounded-full border border-white/15 px-4 py-2 text-sm text-white/70 transition hover:border-[#2cffad]/50 hover:text-[#2cffad]"
          >
            다시 확인
          </button>
        )}
      </div>
    </aside>
  );
}
