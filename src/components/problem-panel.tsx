import type { ProblemPayload } from "@/lib/problem-api";

type ProblemPanelProps = {
  problem: ProblemPayload;
};

export function ProblemPanel({ problem }: ProblemPanelProps) {
  return (
    <article className="h-full overflow-y-auto bg-[#0b1024]/95 px-5 py-6 md:px-7 md:py-8">
      <div className="mb-8 flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-[#ff7a59]/25 bg-[#ff7a59]/8 px-2.5 py-1 font-mono text-[10px] tracking-wider text-[#ffad96]">
          {problem.difficulty.toUpperCase()}
        </span>
        {problem.tags.map((tag) => (
          <span key={tag} className="rounded-full border border-white/8 px-2.5 py-1 font-mono text-[10px] text-white/35">
            #{tag}
          </span>
        ))}
      </div>

      <p className="mb-3 font-mono text-[10px] tracking-[0.2em] text-[#66f7ff]">
        PROBLEM {problem.id} · V{problem.version}
      </p>
      <h1 className="text-3xl font-semibold tracking-[-0.04em] text-[#f4f1e8] md:text-4xl">{problem.title}</h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-white/58">{problem.statement.description}</p>

      {problem.prompt && (
        <aside className="mt-7 rounded-xl border border-[#66f7ff]/20 bg-[#66f7ff]/[0.055] p-4">
          <p className="mb-1 font-mono text-[10px] tracking-[0.16em] text-[#66f7ff]">PSEUDOCODE GUIDE</p>
          <p className="text-sm leading-6 text-white/65">{problem.prompt}</p>
        </aside>
      )}

      <div className="mt-9 grid gap-7">
        <ProblemSection title="입력">
          <p>{problem.statement.input}</p>
        </ProblemSection>
        <ProblemSection title="출력">
          <p>{problem.statement.output}</p>
        </ProblemSection>
        <ProblemSection title="제한 조건">
          <ul className="grid gap-2">
            {problem.statement.constraints.map((constraint) => (
              <li key={constraint} className="flex gap-2">
                <span aria-hidden="true" className="text-[#66f7ff]">›</span>
                <span>{constraint}</span>
              </li>
            ))}
          </ul>
        </ProblemSection>
        <ProblemSection title="예시">
          <div className="grid gap-4">
            {problem.examples.map((example, index) => (
              <div key={`${example.input}-${example.output}`} className="overflow-hidden rounded-xl border border-white/8 bg-black/20">
                <div className="flex items-center justify-between border-b border-white/8 px-4 py-2.5">
                  <span className="font-mono text-[10px] tracking-wider text-white/35">EXAMPLE {index + 1}</span>
                </div>
                <div className="grid sm:grid-cols-2">
                  <ExampleValue label="INPUT" value={example.input} />
                  <ExampleValue label="OUTPUT" value={example.output} bordered />
                </div>
                <p className="border-t border-white/8 px-4 py-3 text-xs leading-5 text-white/40">{example.explanation}</p>
              </div>
            ))}
          </div>
        </ProblemSection>
      </div>
    </article>
  );
}

function ProblemSection({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold text-white/85">{title}</h2>
      <div className="text-sm leading-6 text-white/48">{children}</div>
    </section>
  );
}

function ExampleValue({ bordered = false, label, value }: { bordered?: boolean; label: string; value: string }) {
  return (
    <div className={`p-4 ${bordered ? "border-t border-white/8 sm:border-l sm:border-t-0" : ""}`}>
      <p className="mb-2 font-mono text-[9px] tracking-[0.16em] text-white/25">{label}</p>
      <pre className="overflow-x-auto font-mono text-xs leading-5 text-white/70">{value.trimEnd()}</pre>
    </div>
  );
}
