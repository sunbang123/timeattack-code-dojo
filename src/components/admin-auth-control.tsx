"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import type { AdminAuthController } from "@/hooks/use-admin-auth";

type AdminAuthControlProps = {
  auth: AdminAuthController;
  onSignedOut?: () => void;
};

export function AdminAuthControl({ auth, onSignedOut }: AdminAuthControlProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const close = () => {
    if (working) return;
    setOpen(false);
    setPassword("");
    setMessage(null);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (working || password.length < 8) return;
    setWorking(true);
    setMessage(null);
    try {
      const result =
        mode === "signin"
          ? await auth.signIn(email, password)
          : await auth.signUp(email, password);
      setPassword("");
      if (result.kind === "admin") {
        setOpen(false);
      } else if (result.kind === "confirmation_required") {
        setMessage("인증 메일을 보냈습니다. 이메일 인증 후 로그인해 주세요.");
        setMode("signin");
      } else {
        setMessage("이 계정에는 문제 등록 권한이 없습니다.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "관리자 로그인을 완료하지 못했습니다.");
    } finally {
      setWorking(false);
    }
  };

  if (auth.isAdmin) {
    return (
      <div className="flex items-center gap-2">
        <span className="hidden max-w-44 truncate rounded-full border border-[#d946ef]/25 bg-[#d946ef]/8 px-3 py-1.5 font-mono text-[9px] text-[#eda2ff]/80 md:inline">
          ADMIN · {auth.email}
        </span>
        <button
          className="rounded-lg border border-white/10 px-2.5 py-1.5 text-[10px] text-white/45 transition hover:border-white/25 hover:text-white/75"
          onClick={() => {
            onSignedOut?.();
            void auth.signOut();
          }}
          type="button"
        >
          로그아웃
        </button>
      </div>
    );
  }

  return (
    <>
      <button
        className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-[10px] text-white/50 transition hover:border-[#66f7ff]/30 hover:text-[#98fbff] disabled:cursor-wait disabled:opacity-40"
        disabled={auth.status === "checking"}
        onClick={() => setOpen(true)}
        type="button"
      >
        {auth.status === "checking" ? "관리자 확인 중…" : "관리자 로그인"}
      </button>
      <dialog
        ref={dialogRef}
        className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-2xl border border-white/12 bg-[#10171c] p-0 text-[#f4f1e8] shadow-2xl shadow-black/60 backdrop:bg-black/75 backdrop:backdrop-blur-sm"
        onCancel={(event) => {
          event.preventDefault();
          close();
        }}
      >
        <form className="p-6" onSubmit={submit}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[9px] tracking-[0.2em] text-[#66f7ff]">SUPABASE AUTH</p>
              <h2 className="mt-2 text-xl font-semibold">관리자 계정</h2>
              <p className="mt-1.5 text-xs leading-5 text-white/45">
                로그인된 관리자에게만 문제 추가 메뉴가 표시됩니다.
              </p>
            </div>
            <button
              aria-label="관리자 로그인 창 닫기"
              className="grid size-8 shrink-0 place-items-center rounded-lg border border-white/10 text-white/40 hover:bg-white/5 hover:text-white"
              onClick={close}
              type="button"
            >
              ×
            </button>
          </div>

          <div className="mt-5 grid grid-cols-2 rounded-xl border border-white/10 bg-black/15 p-1">
            {(["signin", "signup"] as const).map((option) => (
              <button
                key={option}
                aria-pressed={mode === option}
                className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                  mode === option ? "bg-white/10 text-white" : "text-white/40 hover:text-white/70"
                }`}
                onClick={() => {
                  setMode(option);
                  setMessage(null);
                }}
                type="button"
              >
                {option === "signin" ? "로그인" : "계정 만들기"}
              </button>
            ))}
          </div>

          <label className="mt-5 block text-xs text-white/55">
            이메일
            <input
              autoComplete="email"
              className="mt-2 w-full rounded-xl border border-white/10 bg-[#090e12] px-3.5 py-2.5 text-sm text-white/85 outline-none focus:border-[#66f7ff]/45 focus:ring-2 focus:ring-[#66f7ff]/15"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label className="mt-4 block text-xs text-white/55">
            비밀번호
            <input
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              className="mt-2 w-full rounded-xl border border-white/10 bg-[#090e12] px-3.5 py-2.5 text-sm text-white/85 outline-none focus:border-[#66f7ff]/45 focus:ring-2 focus:ring-[#66f7ff]/15"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          <p className="mt-2 text-[10px] leading-4 text-white/30">
            {mode === "signup"
              ? "8자 이상의 비밀번호를 설정하고, 받은 메일에서 이메일을 인증해 주세요."
              : "가입할 때 설정한 비밀번호를 입력하세요."}
          </p>

          {auth.message || message ? (
            <p className="mt-4 rounded-lg border border-[#ff7a59]/20 bg-[#ff7a59]/8 px-3 py-2 text-xs leading-5 text-[#ffad96]" role="alert">
              {message ?? auth.message}
            </p>
          ) : null}

          {auth.status === "forbidden" ? (
            <button
              className="mt-4 text-xs text-white/45 underline decoration-white/20 underline-offset-4 hover:text-white/75"
              onClick={() => {
                onSignedOut?.();
                void auth.signOut();
                setMessage(null);
              }}
              type="button"
            >
              다른 계정으로 로그인
            </button>
          ) : null}

          <button
            className="mt-5 w-full rounded-xl bg-[#66f7ff] px-4 py-3 text-sm font-semibold text-[#031316] transition hover:bg-[#9ffaff] disabled:cursor-wait disabled:opacity-45"
            disabled={working}
            type="submit"
          >
            {working ? "처리 중…" : mode === "signin" ? "로그인" : "관리자 계정 만들기"}
          </button>
        </form>
      </dialog>
    </>
  );
}
