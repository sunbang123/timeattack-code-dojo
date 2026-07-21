"use client";

import dynamic from "next/dynamic";
import { loader, type EditorProps, type Monaco } from "@monaco-editor/react";

import type { Language } from "@/lib/problem-api";

loader.config({ paths: { vs: "/monaco/vs" } });

const MonacoEditor = dynamic<EditorProps>(
  () => import("@monaco-editor/react").then((module) => module.default),
  {
    ssr: false,
    loading: () => <EditorLoading />,
  },
);

const editorOptions: EditorProps["options"] = {
  ariaLabel: "코드 답안 편집기",
  automaticLayout: true,
  contextmenu: true,
  fontFamily: '"Geist Mono", "SFMono-Regular", Consolas, monospace',
  fontLigatures: true,
  fontSize: 14,
  lineHeight: 23,
  minimap: { enabled: false },
  padding: { top: 20, bottom: 20 },
  renderLineHighlight: "line",
  roundedSelection: false,
  scrollBeyondLastLine: false,
  smoothScrolling: true,
  tabSize: 4,
  wordWrap: "on",
};

function configureTheme(monaco: Monaco) {
  monaco.editor.defineTheme("dojo-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "comment", foreground: "718078", fontStyle: "italic" },
      { token: "keyword", foreground: "65E6B6" },
      { token: "number", foreground: "FF9C7E" },
      { token: "string", foreground: "D8E67B" },
    ],
    colors: {
      "editor.background": "#090E12",
      "editor.foreground": "#E9E6DD",
      "editor.lineHighlightBackground": "#10181D",
      "editor.selectionBackground": "#245C4A88",
      "editorCursor.foreground": "#2CFFAD",
      "editorLineNumber.foreground": "#3F4C50",
      "editorLineNumber.activeForeground": "#9EB0AA",
      "editorIndentGuide.background1": "#1B272B",
      "editorIndentGuide.activeBackground1": "#334247",
    },
  });
}

function EditorLoading() {
  return (
    <div className="grid h-full min-h-80 place-items-center bg-[#090e12]" aria-live="polite">
      <div className="flex items-center gap-3 font-mono text-xs text-white/45">
        <span className="size-2 animate-pulse rounded-full bg-[#2cffad]" />
        MONACO EDITOR LOADING
      </div>
    </div>
  );
}

type CodeEditorProps = {
  language: Language;
  path: string;
  value: string;
  onChange: (value: string) => void;
};

export function CodeEditor({ language, path, value, onChange }: CodeEditorProps) {
  return (
    <MonacoEditor
      beforeMount={configureTheme}
      height="100%"
      language={language === "cpp" ? "cpp" : "python"}
      onChange={(nextValue) => onChange(nextValue ?? "")}
      options={editorOptions}
      path={path}
      theme="dojo-dark"
      value={value}
    />
  );
}
