import { HealthCheck } from "@/components/health-check";

const modes = [
  {
    index: "01",
    title: "Flash",
    description: "짧은 제한 시간 안에 핵심 구현 감각을 깨웁니다.",
    time: "5분",
  },
  {
    index: "02",
    title: "Standard",
    description: "문제 분석부터 제출까지 한 사이클을 완주합니다.",
    time: "15분",
  },
  {
    index: "03",
    title: "Marathon",
    description: "복합 조건과 리팩터링까지 깊게 파고듭니다.",
    time: "30분",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#070b0f] text-[#f4f1e8]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_70%_12%,rgba(38,255,170,0.12),transparent_28%),radial-gradient(circle_at_8%_78%,rgba(255,91,52,0.1),transparent_24%)]" />
      <div className="relative mx-auto max-w-6xl px-6 py-8 sm:px-10 lg:px-12">
        <header className="flex items-center justify-between border-b border-white/10 pb-6">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-full border border-[#2cffad]/50 bg-[#2cffad]/10 font-mono text-sm text-[#2cffad]">
              T/
            </span>
            <span className="font-mono text-sm tracking-[0.18em] text-white/80">
              TIMEATTACK CODE DOJO
            </span>
          </div>
          <span className="rounded-full border border-white/10 px-3 py-1 font-mono text-[11px] tracking-wider text-white/50">
            STEP 1 · FOUNDATION
          </span>
        </header>

        <section className="grid gap-12 py-16 lg:grid-cols-[1.25fr_0.75fr] lg:items-end lg:py-24">
          <div>
            <p className="mb-5 font-mono text-xs tracking-[0.25em] text-[#2cffad]">
              TRAIN UNDER PRESSURE. SHIP WITH CLARITY.
            </p>
            <h1 className="max-w-4xl text-5xl font-semibold leading-[0.98] tracking-[-0.055em] sm:text-7xl lg:text-[5.5rem]">
              제한 시간은 짧게,
              <br />
              <span className="text-white/38">실력의 흔적은 선명하게.</span>
            </h1>
          </div>
          <div className="lg:pb-2">
            <p className="max-w-md text-base leading-7 text-white/58">
              문제 생성, 실시간 코딩, 자동 채점, AI 피드백을 하나의 훈련 흐름으로 연결하는 개발자용 타임어택 플랫폼입니다.
            </p>
          </div>
        </section>

        <section className="grid gap-5 border-t border-white/10 py-8 lg:grid-cols-[1fr_1.35fr]">
          <HealthCheck />

          <div className="grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-3">
            {modes.map((mode) => (
              <article key={mode.title} className="group bg-[#0b1015] p-6 transition-colors hover:bg-[#10171c]">
                <div className="mb-16 flex items-start justify-between">
                  <span className="font-mono text-xs text-white/35">{mode.index}</span>
                  <span className="rounded-full border border-white/10 px-2.5 py-1 font-mono text-xs text-[#ff7a59]">
                    {mode.time}
                  </span>
                </div>
                <h2 className="mb-2 text-2xl font-medium tracking-tight">{mode.title}</h2>
                <p className="text-sm leading-6 text-white/45">{mode.description}</p>
              </article>
            ))}
          </div>
        </section>

        <footer className="flex flex-col gap-2 border-t border-white/10 pt-6 font-mono text-[11px] tracking-wider text-white/30 sm:flex-row sm:items-center sm:justify-between">
          <span>NEXT.JS 16 + FLASK 3</span>
          <span>READY FOR VERCEL PREVIEW</span>
        </footer>
      </div>
    </main>
  );
}

