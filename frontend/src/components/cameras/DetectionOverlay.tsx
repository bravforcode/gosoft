import { cn } from "@/utils/cn";

export function DetectionOverlay({ critical }: { critical?: boolean }) {
  return (
    <>
      <div className="pointer-events-none absolute inset-4 rounded-[1.4rem] border border-white/10" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-1/3 bg-gradient-to-b from-brand-cyan/10 to-transparent" />
      <div className="pointer-events-none absolute inset-x-4 top-0 h-px animate-scan-line bg-brand-cyan/60" />
      <div className={cn("pointer-events-none absolute inset-0 rounded-[1.6rem] border-2 border-transparent transition", critical && "border-red-500/70 shadow-[0_0_30px_rgba(239,68,68,0.35)]")} />
    </>
  );
}
