"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  createProblem,
  generateProblem,
  type Difficulty,
  type ManualProblemContent,
  type ProblemSummary,
} from "@/lib/problem-api";

type ProblemGeneratorDialogProps = {
  accessToken: string;
  open: boolean;
  onClose: () => void;
  onCreated: (problem: ProblemSummary) => void;
};

type AuthorMode = "ai" | "manual";

type ManualExample = {
  input: string;
  output: string;
  explanation: string;
};

type ManualHiddenTest = {
  input: string;
  expectedOutput: string;
};

type ManualDraft = {
  idSuggestion: string;
  title: string;
  tags: string;
  summary: string;
  description: string;
  input: string;
  output: string;
  constraints: string;
  examples: ManualExample[];
  beginnerPrompt: string;
  rubricCriteria: string;
  intermediatePython: string;
  intermediateCpp: string;
  expertPython: string;
  expertCpp: string;
  referencePython: string;
  referenceCpp: string;
  hiddenTests: ManualHiddenTest[];
};

const difficultyOptions: { value: Difficulty; label: string; caption: string }[] = [
  { value: "easy", label: "쉬움", caption: "기초 구현" },
  { value: "medium", label: "보통", caption: "자료구조·응용" },
  { value: "hard", label: "어려움", caption: "고급 알고리즘" },
];

const inputClassName =
  "mt-2 w-full rounded-xl border border-white/10 bg-[#090e12] px-3.5 py-2.5 text-sm leading-6 text-white/80 outline-none transition placeholder:text-white/20 focus:border-[#66f7ff]/45 focus:ring-2 focus:ring-[#66f7ff]/15";
const codeClassName = `${inputClassName} min-h-36 resize-y font-mono text-xs`;
const initialIntermediatePython = `import sys

def solve():
    # TODO: 입력을 읽고 풀이를 구현하세요.
    pass

if __name__ == "__main__":
    solve()
`;
const initialIntermediateCpp = `#include <iostream>

int main() {
    // TODO: 입력을 읽고 풀이를 구현하세요.
    return 0;
}
`;
const initialExpertPython = `import sys

def solve():
    pass

if __name__ == "__main__":
    solve()
`;
const initialExpertCpp = `#include <iostream>

int main() {
    return 0;
}
`;

function createInitialManualDraft(): ManualDraft {
  return {
    idSuggestion: "",
    title: "",
    tags: "",
    summary: "",
    description: "",
    input: "",
    output: "",
    constraints: "",
    examples: Array.from({ length: 2 }, () => ({
      input: "",
      output: "",
      explanation: "",
    })),
    beginnerPrompt: "",
    rubricCriteria: "",
    intermediatePython: initialIntermediatePython,
    intermediateCpp: initialIntermediateCpp,
    expertPython: initialExpertPython,
    expertCpp: initialExpertCpp,
    referencePython: "",
    referenceCpp: "",
    hiddenTests: Array.from({ length: 3 }, () => ({
      input: "",
      expectedOutput: "",
    })),
  };
}

function nonEmptyLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function buildManualContent(draft: ManualDraft): ManualProblemContent {
  const rubricDescriptions = nonEmptyLines(draft.rubricCriteria);
  const baseWeight = Math.floor(100 / rubricDescriptions.length);
  const remainder = 100 - baseWeight * rubricDescriptions.length;
  return {
    id_suggestion: draft.idSuggestion.trim(),
    title: draft.title.trim(),
    tags: [...new Set(draft.tags.split(",").map((tag) => tag.trim()).filter(Boolean))],
    statement: {
      summary: draft.summary.trim(),
      description: draft.description.trim(),
      input: draft.input.trim(),
      output: draft.output.trim(),
      constraints: nonEmptyLines(draft.constraints),
    },
    examples: draft.examples.map((example) => ({
      input: example.input,
      output: example.output,
      explanation: example.explanation.trim(),
    })),
    beginner_prompt: draft.beginnerPrompt.trim(),
    intermediate_skeletons: {
      python: draft.intermediatePython,
      cpp: draft.intermediateCpp,
    },
    expert_templates: {
      python: draft.expertPython,
      cpp: draft.expertCpp,
    },
    pseudocode_rubric: {
      pass_score: 70,
      criteria: rubricDescriptions.map((description, index) => ({
        id: `step_${index + 1}`,
        description,
        weight: baseWeight + (index < remainder ? 1 : 0),
      })),
    },
    reference_solutions: {
      python: draft.referencePython,
      cpp: draft.referenceCpp,
    },
    hidden_tests: draft.hiddenTests.map((test, index) => ({
      name: `hidden_${index + 1}`,
      input: test.input,
      expected_output: test.expectedOutput,
    })),
  };
}

export function ProblemGeneratorDialog({
  accessToken,
  open,
  onClose,
  onCreated,
}: ProblemGeneratorDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [authorMode, setAuthorMode] = useState<AuthorMode>("ai");
  const [prompt, setPrompt] = useState("");
  const [manualDraft, setManualDraft] = useState(createInitialManualDraft);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    if (isWorking) return;
    setError(null);
    onClose();
  };

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const updateManualDraft = <Key extends keyof ManualDraft>(
    key: Key,
    value: ManualDraft[Key],
  ) => {
    setManualDraft((current) => ({ ...current, [key]: value }));
  };

  const updateExample = (
    index: number,
    key: keyof ManualExample,
    value: string,
  ) => {
    setManualDraft((current) => ({
      ...current,
      examples: current.examples.map((example, exampleIndex) =>
        exampleIndex === index ? { ...example, [key]: value } : example,
      ),
    }));
  };

  const updateHiddenTest = (
    index: number,
    key: keyof ManualHiddenTest,
    value: string,
  ) => {
    setManualDraft((current) => ({
      ...current,
      hiddenTests: current.hiddenTests.map((test, testIndex) =>
        testIndex === index ? { ...test, [key]: value } : test,
      ),
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isWorking) return;
    if (authorMode === "ai" && prompt.trim().length < 10) return;
    if (authorMode === "manual") {
      const rubricCount = nonEmptyLines(manualDraft.rubricCriteria).length;
      if (rubricCount < 3 || rubricCount > 6) {
        setError("채점 핵심 단계는 줄마다 하나씩, 3개 이상 6개 이하로 입력해 주세요.");
        return;
      }
    }

    setIsWorking(true);
    setError(null);
    try {
      const result =
        authorMode === "ai"
          ? await generateProblem(prompt.trim(), difficulty, accessToken)
          : await createProblem(
              buildManualContent(manualDraft),
              difficulty,
              accessToken,
            );
      if (authorMode === "ai") {
        setPrompt("");
      } else {
        setManualDraft(createInitialManualDraft());
      }
      onCreated(result.problem);
    } catch (creationError) {
      setError(
        creationError instanceof Error
          ? creationError.message
          : "문제를 만들지 못했습니다.",
      );
    } finally {
      setIsWorking(false);
    }
  };

  const manualMode = authorMode === "manual";

  return (
    <dialog
      ref={dialogRef}
      className="m-auto w-[calc(100%-2rem)] max-w-5xl rounded-2xl border border-white/12 bg-[#10171c] p-0 text-[#f4f1e8] shadow-2xl shadow-black/60 backdrop:bg-black/75 backdrop:backdrop-blur-sm"
      onCancel={(event) => {
        event.preventDefault();
        handleClose();
      }}
    >
      <form
        aria-labelledby="generator-title"
        className="flex max-h-[calc(100vh-2rem)] flex-col"
        onSubmit={handleSubmit}
      >
        <div className="shrink-0 border-b border-white/10 px-5 py-5 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[9px] tracking-[0.2em] text-[#66f7ff]">
                {manualMode ? "MANUAL · PROBLEM AUTHOR" : "HUGGING FACE · AI AUTHOR"}
              </p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight" id="generator-title">
                새 문제 만들기
              </h2>
              <p className="mt-1.5 text-xs leading-5 text-white/45">
                {manualMode
                  ? "문제와 채점 데이터를 직접 입력해 문제은행에 등록합니다."
                  : "주제와 조건을 적으면 문제·예제·채점 데이터를 함께 생성합니다."}
              </p>
            </div>
            <button
              aria-label="문제 생성 창 닫기"
              className="grid size-8 shrink-0 place-items-center rounded-lg border border-white/10 text-white/40 transition hover:bg-white/5 hover:text-white disabled:opacity-30"
              disabled={isWorking}
              onClick={handleClose}
              type="button"
            >
              ×
            </button>
          </div>
        </div>

        <fieldset className="min-h-0 overflow-y-auto border-0 p-0" disabled={isWorking}>
          <div className="space-y-6 px-5 py-5 sm:px-6">
            <div className="grid grid-cols-2 rounded-xl border border-white/10 bg-black/15 p-1" role="tablist" aria-label="문제 작성 방식">
              {(["ai", "manual"] as const).map((mode) => {
                const active = authorMode === mode;
                return (
                  <button
                    key={mode}
                    aria-selected={active}
                    className={`rounded-lg px-4 py-2.5 text-xs font-semibold transition ${
                      active
                        ? "bg-white/10 text-white shadow-sm"
                        : "text-white/40 hover:text-white/70"
                    }`}
                    onClick={() => {
                      setAuthorMode(mode);
                      setError(null);
                    }}
                    role="tab"
                    type="button"
                  >
                    {mode === "ai" ? "AI로 생성" : "직접 입력"}
                  </button>
                );
              })}
            </div>

            <fieldset>
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
                      className={`rounded-xl border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#66f7ff]/60 ${
                        active
                          ? "border-[#66f7ff]/45 bg-[#66f7ff]/9 text-[#98fbff]"
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

            {manualMode ? (
              <ManualProblemFields
                draft={manualDraft}
                onExampleChange={updateExample}
                onFieldChange={updateManualDraft}
                onHiddenTestChange={updateHiddenTest}
              />
            ) : (
              <label className="block">
                <span className="font-mono text-[10px] tracking-[0.16em] text-white/45">
                  문제 요청
                </span>
                <textarea
                  autoFocus
                  className={`${inputClassName} min-h-36 resize-y`}
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
            )}

            {error ? (
              <p className="rounded-lg border border-[#ff7a59]/25 bg-[#ff7a59]/8 px-3 py-2.5 text-xs leading-5 text-[#ffad96]" role="alert">
                {error}
              </p>
            ) : null}
          </div>
        </fieldset>

        <div className="flex shrink-0 items-center justify-between gap-3 border-t border-white/10 bg-[#10171c] px-5 py-4 sm:px-6">
          <p className="hidden text-[10px] text-white/30 sm:block">
            {manualMode
              ? "저장 전 Python·C++ 정답을 모든 테스트로 검증합니다."
              : "생성에는 최대 1분 정도 걸릴 수 있어요."}
          </p>
          <div className="ml-auto flex gap-2">
            <button
              className="rounded-lg border border-white/12 px-4 py-2.5 text-xs text-white/60 transition hover:bg-white/5 hover:text-white disabled:opacity-30"
              disabled={isWorking}
              onClick={handleClose}
              type="button"
            >
              취소
            </button>
            <button
              className="min-w-28 rounded-lg bg-[#66f7ff] px-4 py-2.5 text-xs font-semibold text-[#041318] transition hover:bg-[#98fbff] disabled:cursor-not-allowed disabled:bg-white/[0.06] disabled:text-white/25"
              disabled={isWorking || (!manualMode && prompt.trim().length < 10)}
              type="submit"
            >
              {isWorking
                ? manualMode
                  ? "검증·저장 중…"
                  : "문제 생성 중…"
                : manualMode
                  ? "문제 저장"
                  : "AI로 생성"}
            </button>
          </div>
        </div>
      </form>
    </dialog>
  );
}

function ManualProblemFields({
  draft,
  onExampleChange,
  onFieldChange,
  onHiddenTestChange,
}: {
  draft: ManualDraft;
  onExampleChange: (index: number, key: keyof ManualExample, value: string) => void;
  onFieldChange: <Key extends keyof ManualDraft>(
    key: Key,
    value: ManualDraft[Key],
  ) => void;
  onHiddenTestChange: (
    index: number,
    key: keyof ManualHiddenTest,
    value: string,
  ) => void;
}) {
  return (
    <div className="space-y-8">
      <ManualSection
        description="문제 목록과 URL에서 사용할 식별 정보입니다."
        title="1. 기본 정보"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            autoFocus
            label="문제 제목"
            maxLength={80}
            onChange={(value) => onFieldChange("title", value)}
            placeholder="예: 가장 짧은 연속 구간"
            value={draft.title}
          />
          <TextField
            label="문제 ID"
            maxLength={64}
            onChange={(value) => onFieldChange("idSuggestion", value)}
            pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
            placeholder="shortest-subarray"
            value={draft.idSuggestion}
          />
        </div>
        <TextField
          label="태그 (쉼표로 구분, 최대 6개)"
          onChange={(value) => onFieldChange("tags", value)}
          placeholder="two-pointers, array"
          value={draft.tags}
        />
      </ManualSection>

      <ManualSection
        description="풀이 화면에 그대로 노출되는 본문입니다."
        title="2. 문제 설명"
      >
        <TextAreaField
          label="한 줄 요약"
          onChange={(value) => onFieldChange("summary", value)}
          placeholder="어떤 값을 구해야 하는지 한 문장으로 적어 주세요."
          value={draft.summary}
        />
        <TextAreaField
          label="상세 설명"
          onChange={(value) => onFieldChange("description", value)}
          placeholder="문제 상황과 정답 조건을 모호함 없이 설명해 주세요."
          value={draft.description}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextAreaField
            label="입력 형식"
            onChange={(value) => onFieldChange("input", value)}
            placeholder="첫째 줄에 N과 S가 주어집니다."
            value={draft.input}
          />
          <TextAreaField
            label="출력 형식"
            onChange={(value) => onFieldChange("output", value)}
            placeholder="정답을 한 줄에 출력합니다."
            value={draft.output}
          />
        </div>
        <TextAreaField
          label="제약 조건 (줄마다 하나, 최대 8개)"
          onChange={(value) => onFieldChange("constraints", value)}
          placeholder={"1 ≤ N ≤ 100,000\n모든 입력은 정수입니다."}
          value={draft.constraints}
        />
      </ManualSection>

      <ManualSection
        description="공개 예제는 정답 코드 검증에도 사용됩니다."
        title="3. 공개 예제"
      >
        <div className="grid gap-4 lg:grid-cols-2">
          {draft.examples.map((example, index) => (
            <div className="space-y-3 rounded-xl border border-white/8 bg-black/10 p-4" key={index}>
              <p className="font-mono text-[10px] tracking-wider text-[#98fbff]/70">
                EXAMPLE {index + 1}
              </p>
              <TextAreaField
                code
                label="입력"
                onChange={(value) => onExampleChange(index, "input", value)}
                value={example.input}
              />
              <TextAreaField
                code
                label="출력"
                onChange={(value) => onExampleChange(index, "output", value)}
                value={example.output}
              />
              <TextAreaField
                label="설명"
                onChange={(value) => onExampleChange(index, "explanation", value)}
                value={example.explanation}
              />
            </div>
          ))}
        </div>
      </ManualSection>

      <ManualSection
        description="초급자는 의사코드, 중수·고수는 코드로 풉니다. TODO 표시는 유지해 주세요."
        title="4. 모드별 출제 설정"
      >
        <TextAreaField
          label="초급자 의사코드 안내"
          onChange={(value) => onFieldChange("beginnerPrompt", value)}
          placeholder="필수 단계와 예외 처리를 순서대로 작성하세요."
          value={draft.beginnerPrompt}
        />
        <TextAreaField
          label="초급자 채점 핵심 단계 (줄마다 하나, 3~6개)"
          onChange={(value) => onFieldChange("rubricCriteria", value)}
          placeholder={"입력을 읽고 필요한 상태를 초기화한다.\n조건에 따라 상태를 갱신한다.\n최종 정답을 출력한다."}
          value={draft.rubricCriteria}
        />
        <CodePair
          cpp={draft.intermediateCpp}
          description="풀이 뼈대만 제공하고 구현할 위치에 TODO를 포함합니다."
          onCppChange={(value) => onFieldChange("intermediateCpp", value)}
          onPythonChange={(value) => onFieldChange("intermediatePython", value)}
          python={draft.intermediatePython}
          title="중수 시작 코드"
        />
        <CodePair
          cpp={draft.expertCpp}
          description="풀이 힌트 없이 입출력 진입점만 제공하는 최소 템플릿입니다."
          onCppChange={(value) => onFieldChange("expertCpp", value)}
          onPythonChange={(value) => onFieldChange("expertPython", value)}
          python={draft.expertPython}
          title="고수 시작 코드"
        />
      </ManualSection>

      <ManualSection
        description="저장 시 두 정답 코드를 공개 예제와 숨은 테스트 전체로 실행합니다."
        title="5. 비공개 채점 데이터"
      >
        <CodePair
          cpp={draft.referenceCpp}
          description="모든 테스트를 통과하는 완성된 풀이를 입력하세요."
          onCppChange={(value) => onFieldChange("referenceCpp", value)}
          onPythonChange={(value) => onFieldChange("referencePython", value)}
          python={draft.referencePython}
          title="정답 코드"
        />
        <div className="grid gap-4 lg:grid-cols-3">
          {draft.hiddenTests.map((test, index) => (
            <div className="space-y-3 rounded-xl border border-white/8 bg-black/10 p-4" key={index}>
              <p className="font-mono text-[10px] tracking-wider text-[#d946ef]/80">
                HIDDEN {index + 1}
              </p>
              <TextAreaField
                code
                label="입력"
                onChange={(value) => onHiddenTestChange(index, "input", value)}
                value={test.input}
              />
              <TextAreaField
                code
                label="예상 출력"
                onChange={(value) => onHiddenTestChange(index, "expectedOutput", value)}
                value={test.expectedOutput}
              />
            </div>
          ))}
        </div>
      </ManualSection>
    </div>
  );
}

function ManualSection({
  children,
  description,
  title,
}: {
  children: React.ReactNode;
  description: string;
  title: string;
}) {
  return (
    <section className="space-y-4 border-t border-white/8 pt-6 first:border-0 first:pt-0">
      <div>
        <h3 className="text-sm font-semibold text-white/85">{title}</h3>
        <p className="mt-1 text-[11px] leading-5 text-white/35">{description}</p>
      </div>
      {children}
    </section>
  );
}

function TextField({
  autoFocus,
  label,
  maxLength,
  onChange,
  pattern,
  placeholder,
  value,
}: {
  autoFocus?: boolean;
  label: string;
  maxLength?: number;
  onChange: (value: string) => void;
  pattern?: string;
  placeholder?: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="font-mono text-[10px] tracking-[0.12em] text-white/45">{label}</span>
      <input
        autoFocus={autoFocus}
        className={inputClassName}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        pattern={pattern}
        placeholder={placeholder}
        required
        type="text"
        value={value}
      />
    </label>
  );
}

function TextAreaField({
  code = false,
  label,
  onChange,
  placeholder,
  value,
}: {
  code?: boolean;
  label: string;
  onChange: (value: string) => void;
  placeholder?: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="font-mono text-[10px] tracking-[0.12em] text-white/45">{label}</span>
      <textarea
        className={`${inputClassName} ${code ? "min-h-24 font-mono text-xs" : "min-h-24"} resize-y`}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required
        spellCheck={!code}
        value={value}
      />
    </label>
  );
}

function CodePair({
  cpp,
  description,
  onCppChange,
  onPythonChange,
  python,
  title,
}: {
  cpp: string;
  description: string;
  onCppChange: (value: string) => void;
  onPythonChange: (value: string) => void;
  python: string;
  title: string;
}) {
  return (
    <div className="space-y-3 rounded-xl border border-white/8 bg-black/10 p-4">
      <div>
        <h4 className="text-xs font-semibold text-white/70">{title}</h4>
        <p className="mt-1 text-[10px] leading-4 text-white/30">{description}</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <label className="block">
          <span className="font-mono text-[10px] tracking-[0.12em] text-[#98fbff]/65">PYTHON</span>
          <textarea
            className={codeClassName}
            onChange={(event) => onPythonChange(event.target.value)}
            required
            spellCheck={false}
            value={python}
          />
        </label>
        <label className="block">
          <span className="font-mono text-[10px] tracking-[0.12em] text-[#eda2ff]/65">C++17</span>
          <textarea
            className={codeClassName}
            onChange={(event) => onCppChange(event.target.value)}
            required
            spellCheck={false}
            value={cpp}
          />
        </label>
      </div>
    </div>
  );
}
