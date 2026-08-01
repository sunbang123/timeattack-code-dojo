"use client";

import { useCallback, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";

import { fetchAdminSession, ProblemApiError } from "@/lib/problem-api";
import { getSupabaseBrowserClient } from "@/lib/supabase-client";

type AdminAuthStatus =
  | "checking"
  | "signed_out"
  | "admin"
  | "forbidden"
  | "error";

type AdminAuthState = {
  status: AdminAuthStatus;
  accessToken: string | null;
  email: string | null;
  message: string | null;
};

export type AdminAuthResult =
  | { kind: "admin" }
  | { kind: "forbidden" }
  | { kind: "confirmation_required" };

export type AdminAuthController = AdminAuthState & {
  isAdmin: boolean;
  signIn: (email: string, password: string) => Promise<AdminAuthResult>;
  signOut: () => Promise<void>;
  signUp: (email: string, password: string) => Promise<AdminAuthResult>;
};

const signedOutState: AdminAuthState = {
  status: "signed_out",
  accessToken: null,
  email: null,
  message: null,
};

function authErrorMessage(message: string): string {
  const normalized = message.toLowerCase();
  if (normalized.includes("invalid login credentials")) {
    return "이메일 또는 비밀번호가 올바르지 않습니다.";
  }
  if (normalized.includes("email not confirmed")) {
    return "이메일 인증을 완료한 뒤 로그인해 주세요.";
  }
  if (normalized.includes("user already registered")) {
    return "이미 가입된 이메일입니다. 로그인해 주세요.";
  }
  return message;
}

async function resolveAdminState(session: Session | null): Promise<AdminAuthState> {
  if (!session) return signedOutState;
  try {
    const verified = await fetchAdminSession(session.access_token);
    return {
      status: "admin",
      accessToken: session.access_token,
      email: verified.email,
      message: null,
    };
  } catch (error) {
    if (error instanceof ProblemApiError && error.status === 403) {
      return {
        status: "forbidden",
        accessToken: null,
        email: session.user.email ?? null,
        message: "이 계정에는 문제 등록 권한이 없습니다.",
      };
    }
    if (error instanceof ProblemApiError && error.status === 401) {
      return signedOutState;
    }
    return {
      status: "error",
      accessToken: null,
      email: session.user.email ?? null,
      message:
        error instanceof Error
          ? error.message
          : "관리자 권한을 확인하지 못했습니다.",
    };
  }
}

export function useAdminAuth(): AdminAuthController {
  const [state, setState] = useState<AdminAuthState>({
    status: "checking",
    accessToken: null,
    email: null,
    message: null,
  });

  useEffect(() => {
    let active = true;
    let client;
    try {
      client = getSupabaseBrowserClient();
    } catch (error) {
      queueMicrotask(() => {
        if (!active) return;
        setState({
          status: "error",
          accessToken: null,
          email: null,
          message: error instanceof Error ? error.message : "관리자 로그인을 시작하지 못했습니다.",
        });
      });
      return;
    }

    const syncSession = (session: Session | null) => {
      void resolveAdminState(session).then((nextState) => {
        if (active) setState(nextState);
      });
    };
    void client.auth.getSession().then(({ data }) => syncSession(data.session));
    const { data } = client.auth.onAuthStateChange((_event, session) => {
      syncSession(session);
    });
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const client = getSupabaseBrowserClient();
    const { data, error } = await client.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    if (error) throw new Error(authErrorMessage(error.message));
    const nextState = await resolveAdminState(data.session);
    setState(nextState);
    return { kind: nextState.status === "admin" ? "admin" : "forbidden" } as const;
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const client = getSupabaseBrowserClient();
    const { data, error } = await client.auth.signUp({
      email: email.trim(),
      password,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) throw new Error(authErrorMessage(error.message));
    if (!data.session) return { kind: "confirmation_required" } as const;
    const nextState = await resolveAdminState(data.session);
    setState(nextState);
    return { kind: nextState.status === "admin" ? "admin" : "forbidden" } as const;
  }, []);

  const signOut = useCallback(async () => {
    const client = getSupabaseBrowserClient();
    await client.auth.signOut();
    setState(signedOutState);
  }, []);

  return {
    ...state,
    isAdmin: state.status === "admin" && Boolean(state.accessToken),
    signIn,
    signOut,
    signUp,
  };
}
