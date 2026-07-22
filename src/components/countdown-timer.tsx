"use client";

import { useEffect, useState } from "react";

type CountdownTimerProps = {
  durationSeconds: number;
};

function normalizeDuration(durationSeconds: number) {
  return Math.max(0, Math.floor(durationSeconds));
}

function formatTime(remainingSeconds: number) {
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function getTimerState(remainingSeconds: number) {
  if (remainingSeconds === 0) {
    return {
      label: "TIME UP",
      shell: "border-[#ff5f52]/55 bg-[#ff5f52]/12 shadow-[0_0_24px_rgba(255,95,82,0.1)]",
      dot: "bg-[#ff5f52]",
      text: "text-[#ff8b80]",
    };
  }
  if (remainingSeconds <= 60) {
    return {
      label: "HURRY UP",
      shell: "border-[#ff7a59]/45 bg-[#ff7a59]/10",
      dot: "animate-pulse bg-[#ff7a59]",
      text: "text-[#ffad96]",
    };
  }
  if (remainingSeconds <= 300) {
    return {
      label: "TIME LEFT",
      shell: "border-[#ffc857]/30 bg-[#ffc857]/7",
      dot: "bg-[#ffc857]",
      text: "text-[#ffd980]",
    };
  }
  return {
    label: "TIME LEFT",
    shell: "border-[#2cffad]/25 bg-[#2cffad]/7",
    dot: "bg-[#2cffad]",
    text: "text-[#7dffcc]",
  };
}

export function CountdownTimer({ durationSeconds }: CountdownTimerProps) {
  const duration = normalizeDuration(durationSeconds);
  const [remainingSeconds, setRemainingSeconds] = useState(duration);

  useEffect(() => {
    if (duration === 0) return;
    const deadline = Date.now() + duration * 1000;
    const timerId = window.setInterval(() => {
      const nextRemainingSeconds = Math.max(
        0,
        Math.ceil((deadline - Date.now()) / 1000),
      );
      setRemainingSeconds(nextRemainingSeconds);
      if (nextRemainingSeconds === 0) window.clearInterval(timerId);
    }, 250);
    return () => window.clearInterval(timerId);
  }, [duration]);

  const formattedTime = formatTime(remainingSeconds);
  const state = getTimerState(remainingSeconds);

  return (
    <div
      aria-label={`남은 제한시간 ${formattedTime}`}
      className={`flex min-w-[8.6rem] items-center gap-2.5 rounded-lg border px-3 py-2 transition-colors ${state.shell}`}
      role="timer"
    >
      <span aria-hidden="true" className={`size-1.5 rounded-full ${state.dot}`} />
      <span className="flex flex-col leading-none">
        <span className="font-mono text-[8px] tracking-[0.18em] text-white/35">
          {state.label}
        </span>
        <span
          className={`mt-1 font-mono text-lg font-semibold tracking-[0.08em] tabular-nums ${state.text}`}
        >
          {formattedTime}
        </span>
      </span>
    </div>
  );
}
