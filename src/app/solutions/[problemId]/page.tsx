import Link from "next/link";

import { SolutionWorkspace } from "@/components/solution-workspace";
import {
  LANGUAGES,
  MODES,
  type Language,
  type Mode,
} from "@/lib/problem-api";

type SolutionPageProps = {
  params: Promise<{ problemId: string }>;
  searchParams: Promise<{
    version?: string | string[];
    mode?: string | string[];
    language?: string | string[];
  }>;
};

export default async function SolutionPage({ params, searchParams }: SolutionPageProps) {
  const [{ problemId }, query] = await Promise.all([params, searchParams]);
  const versionText = singleValue(query.version);
  const mode = singleValue(query.mode);
  const language = singleValue(query.language);
  const version = Number(versionText);

  const validScope =
    /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(problemId) &&
    Number.isInteger(version) &&
    version >= 1 &&
    MODES.includes(mode as Mode) &&
    LANGUAGES.includes(language as Language);

  if (!validScope) {
    return <InvalidSolutionLink />;
  }

  return (
    <SolutionWorkspace
      scope={{
        id: problemId,
        version,
        mode: mode as Mode,
        language: language as Language,
      }}
    />
  );
}

function singleValue(value: string | string[] | undefined): string {
  return typeof value === "string" ? value : "";
}

function InvalidSolutionLink() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#070b0f] px-5 text-center text-[#f4f1e8]">
      <div className="max-w-md">
        <p className="font-mono text-xs tracking-[0.18em] text-[#ff9b80]">INVALID SOLUTION LINK</p>
        <h1 className="mt-4 text-2xl font-semibold">풀이 링크가 올바르지 않습니다.</h1>
        <Link className="mt-6 inline-flex rounded-lg bg-[#2cffad] px-5 py-3 text-sm font-semibold text-[#03140e]" href="/">
          문제로 돌아가기
        </Link>
      </div>
    </main>
  );
}
