import { cn } from "../lib/utils";

export default function BrandMark({ className }) {
  return (
    <div
      className={cn(
        "w-9 h-9 rounded-xl bg-slate-800 text-white flex items-center justify-center shrink-0 text-sm font-bold tracking-tight",
        className
      )}
      aria-hidden
    >
      WC
    </div>
  );
}
