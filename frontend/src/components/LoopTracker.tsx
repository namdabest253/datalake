import { Icon } from "@/components/Icon";
import type { ActiveTrace, PassSummary } from "@/api/client";

const PASS_LABELS: Record<PassSummary["pass"], string> = {
  READ: "Read & Extract",
  PROPOSE: "Propose Hypotheses",
  CRITIQUE: "Multi-Agent Critique",
  REFINE: "Refine Syntheses",
  VOTE: "Vote on Winner",
  ENRICH: "Enrich Payload",
};

type Props = {
  trace: ActiveTrace | null;
  loading: boolean;
  error: string | null;
};

export function LoopTracker({ trace, loading, error }: Props) {
  const headerText = loading
    ? "Active Trace: loading…"
    : error
      ? `Active Trace: API error (${error})`
      : !trace || !trace.available
        ? "Active Trace: (no trace events yet)"
        : `Active Trace: ${trace.filename}`;

  const passes = trace?.available ? trace.passes : null;

  return (
    <div className="flex flex-col h-full">
      <div className="text-label-caps text-on-surface-variant mb-6 border-b border-outline-variant pb-2 truncate" title={headerText}>
        {headerText}
      </div>
      <div className="flex-1 relative flex flex-col justify-between pl-8">
        <div className="absolute left-[11px] top-4 bottom-4 w-px bg-outline-variant z-0" />
        {passes
          ? passes.map((p) => (
              <LoopStep
                key={p.pass}
                label={PASS_LABELS[p.pass]}
                done={p.state === "done"}
                active={p.state === "active"}
                failed={p.state === "failed"}
                muted={p.state === "pending"}
                sub={
                  p.state === "pending"
                    ? undefined
                    : `${p.ok} ok${p.failed ? `, ${p.failed} failed` : ""}` +
                      (p.latency_ms !== null ? ` · ${p.latency_ms}ms` : "")
                }
              >
                {p.pass === "PROPOSE" && p.ok > 0 ? (
                  <div className="flex gap-2 mt-2">
                    {Array.from({ length: p.ok }).map((_, i) => (
                      <div
                        key={i}
                        className="w-8 h-8 rounded border border-outline flex items-center justify-center bg-surface text-secondary"
                      >
                        <Icon name="psychology" className="text-[16px]" />
                      </div>
                    ))}
                  </div>
                ) : null}
                {p.pass === "CRITIQUE" && (p.ok > 0 || p.failed > 0) ? (
                  <div className="flex gap-2 mt-2">
                    {p.failed > 0 && (
                      <div className="px-2 py-1 rounded bg-error-container text-on-error-container text-label-sm flex items-center gap-1">
                        <Icon name="close" className="text-[12px]" /> Reject {p.failed}
                      </div>
                    )}
                    {p.ok > 0 && (
                      <div className="px-2 py-1 rounded bg-secondary-container text-on-secondary-container text-label-sm flex items-center gap-1">
                        <Icon name="check" className="text-[12px]" /> Accept {p.ok}
                      </div>
                    )}
                  </div>
                ) : null}
              </LoopStep>
            ))
          : (Object.keys(PASS_LABELS) as PassSummary["pass"][]).map((p) => (
              <LoopStep key={p} label={PASS_LABELS[p]} muted />
            ))}
      </div>
    </div>
  );
}

function LoopStep({
  done,
  active,
  failed,
  muted,
  label,
  sub,
  children,
}: {
  done?: boolean;
  active?: boolean;
  failed?: boolean;
  muted?: boolean;
  label: string;
  sub?: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={`relative z-10 flex items-start gap-4 ${muted ? "opacity-50" : ""}`}
    >
      <div className="relative w-6 h-6 shrink-0 mt-1">
        {active && (
          // Spinning rim — sits one pixel outside the inner circle so the rim
          // visibly orbits while the pass is in-flight. Only on truly-active
          // passes; "failed" passes get a static red indicator below.
          <span
            aria-hidden
            className="absolute -inset-[3px] rounded-full border-2 border-secondary/30 border-t-secondary animate-spin [animation-duration:1.1s]"
          />
        )}
        <div
          className={`relative w-6 h-6 rounded-full flex items-center justify-center ${
            done
              ? "bg-secondary"
              : failed
                ? "bg-surface border-2 border-error"
                : active
                  ? "bg-surface border-2 border-secondary"
                  : "bg-surface border-2 border-outline-variant"
          }`}
        >
          {done ? (
            <Icon name="check" className="text-[14px] text-on-secondary" />
          ) : failed ? (
            <Icon name="close" className="text-[14px] text-error" />
          ) : active ? (
            <div className="w-2 h-2 rounded-full bg-secondary animate-flash" />
          ) : null}
        </div>
      </div>
      <div className="w-full">
        <div
          className={`text-label-caps ${
            failed ? "text-error" : active ? "text-primary" : "text-on-surface"
          }`}
        >
          {label}
        </div>
        {sub && (
          <div className="text-label-sm font-mono text-outline mt-1">{sub}</div>
        )}
        {children}
      </div>
    </div>
  );
}
