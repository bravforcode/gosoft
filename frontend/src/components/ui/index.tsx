import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, PropsWithChildren, ReactNode, SelectHTMLAttributes } from "react";

import { cn } from "@/utils/cn";

export function Button({ className, children, ...props }: PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>>) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-xl border border-white/10 bg-brand-blue px-4 py-2 text-sm font-medium text-white transition hover:bg-[#1f69ff] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Card({ className, children, ...props }: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div className={cn("glass-panel rounded-2xl p-5", className)} {...props}>
      {children}
    </div>
  );
}

export function Badge({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <span className={cn("inline-flex rounded-full border border-white/10 px-2.5 py-1 text-xs font-medium uppercase tracking-[0.18em] text-slate-200", className)}>{children}</span>;
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-brand-cyan focus:ring-0" {...props} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-brand-cyan focus:ring-0" {...props} />;
}

export function Progress({ value }: { value: number }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
      <div className="h-full rounded-full bg-gradient-to-r from-brand-cyan to-brand-blue transition-all duration-500" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

export function SectionTitle({ title, eyebrow, action }: { title: string; eyebrow?: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-4">
      <div>
        {eyebrow ? <p className="font-mono text-xs uppercase tracking-[0.24em] text-brand-cyan">{eyebrow}</p> : null}
        <h2 className="font-display text-3xl uppercase tracking-[0.08em] text-white">{title}</h2>
      </div>
      {action}
    </div>
  );
}
