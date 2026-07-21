"use client";

import { useEffect, useRef } from "react";

type DiscardDialogProps = {
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function DiscardDialog({ open, onCancel, onConfirm }: DiscardDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-white/12 bg-[#10171c] p-6 text-[#f4f1e8] shadow-2xl shadow-black/60 backdrop:bg-black/75 backdrop:backdrop-blur-sm"
      onCancel={(event) => {
        event.preventDefault();
        onCancel();
      }}
    >
      <section
        aria-describedby="discard-description"
        aria-labelledby="discard-title"
      >
        <span className="mb-5 grid size-10 place-items-center rounded-full border border-[#ff7a59]/30 bg-[#ff7a59]/10 font-mono text-[#ff9b80]">!</span>
        <h2 id="discard-title" className="text-xl font-semibold tracking-tight text-white">작성 중인 답안이 있어요</h2>
        <p id="discard-description" className="mt-2 text-sm leading-6 text-white/50">
          문제, 모드 또는 언어를 바꾸면 현재 답안이 초기화됩니다. 변경을 계속할까요?
        </p>
        <div className="mt-7 flex justify-end gap-2">
          <button
            autoFocus
            className="rounded-lg border border-white/12 px-4 py-2.5 text-sm text-white/65 transition hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
            onClick={onCancel}
            type="button"
          >
            계속 작성
          </button>
          <button
            className="rounded-lg bg-[#ff7a59] px-4 py-2.5 text-sm font-semibold text-[#190804] transition hover:bg-[#ff967c] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb7a5]"
            onClick={onConfirm}
            type="button"
          >
            답안 버리고 변경
          </button>
        </div>
      </section>
    </dialog>
  );
}
