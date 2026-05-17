import { Icon } from "@/components/Icon";
import { GlassCard } from "@/components/GlassCard";
import { api, type PassSummary } from "@/api/client";
import { useApi } from "@/api/useApi";

// Display labels and sub-copy keyed on the pass name. The state machine writes one
// trace_events row per (pass, proposal_idx); the API aggregates these into a single
// PassSummary per pass. We render one LoopStep per pass.
const PASS_LABELS: Record<PassSummary["pass"], string> = {
  READ: "Read & Extract",
  PROPOSE: "Propose Hypotheses",
  CRITIQUE: "Multi-Agent Critique",
  REFINE: "Refine Syntheses",
  VOTE: "Vote on Winner",
  ENRICH: "Enrich Payload",
};

const STATUS_STYLES: Record<
  string,
  { dot: string; text: string }
> = {
  Ready: { dot: "bg-secondary animate-flash", text: "text-secondary" },
  Extracting: { dot: "bg-secondary animate-flash", text: "text-secondary" },
  Failed: { dot: "bg-error", text: "text-error" },
  Queued: { dot: "bg-outline", text: "text-outline" },
};

function fmtUSD(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(2)}K`;
  if (n >= 1) return `$${n.toFixed(2)}`;
  return `$${n.toFixed(4)}`;
}

export default function Dashboard() {
  const stream = useApi(() => api.stream(undefined, 20), []);
  const counters = useApi(() => api.counters(), []);
  const trace = useApi(() => api.activeTrace(), []);

  // Cost-bar fill is wafer/gpt4 ratio expressed as percentage of the GPT-4 bar.
  const wafer = counters.data?.wafer_usd ?? 0;
  const gpt4 = counters.data?.gpt4_equivalent_usd ?? 0;
  const ratio = counters.data?.cost_ratio_vs_gpt4 ?? null;
  const fillPct = gpt4 > 0 ? Math.max(0.5, (wafer / gpt4) * 100) : 0;
  const items = stream.data ?? [];
  const interAgentPct = Math.round((counters.data?.avg_overall_confidence ?? 0) * 100);
  const overallConfPct = interAgentPct;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      {/* Center: Live Document Stream */}
      <div className="lg:col-span-8 flex flex-col gap-unit">
        <h2 className="text-headline-sm text-on-surface mb-4">
          Live Ingestion Stream
        </h2>
        <GlassCard className="p-1 flex flex-col gap-1 overflow-hidden h-[500px]">
          <div className="grid grid-cols-12 gap-4 px-4 py-2 bg-surface-container-low rounded-t-lg border-b border-outline-variant">
            <div className="col-span-6 text-label-caps text-on-surface-variant">
              Document Identity
            </div>
            <div className="col-span-3 text-label-caps text-on-surface-variant">
              Classification
            </div>
            <div className="col-span-3 text-label-caps text-on-surface-variant text-right">
              Pipeline Status
            </div>
          </div>
          <div className="overflow-y-auto pr-2 space-y-1">
            {stream.loading && (
              <div className="px-4 py-6 text-on-surface-variant text-label-caps">
                Loading documents…
              </div>
            )}
            {stream.error && (
              <div className="px-4 py-6 text-error text-label-caps">
                API error: {stream.error}. Is `datalake api` running?
              </div>
            )}
            {!stream.loading && !stream.error && items.length === 0 && (
              <div className="px-4 py-6 text-on-surface-variant text-label-caps">
                No documents in this run yet.
              </div>
            )}
            {items.map((item) => {
              const styles = STATUS_STYLES[item.status];
              return (
                <div
                  key={item.id}
                  className="grid grid-cols-12 gap-4 px-4 py-3 bg-surface hover:bg-surface-container-low transition-colors rounded border border-transparent hover:border-outline-variant items-center group cursor-pointer relative overflow-hidden"
                >
                  <div
                    className={`absolute left-0 top-0 bottom-0 w-1 ${
                      item.status === "Failed" ? "bg-error" : "bg-secondary"
                    } opacity-0 group-hover:opacity-100 transition-opacity`}
                  />
                  <div className="col-span-6 flex items-center gap-3">
                    <Icon
                      name={item.iconName}
                      className={
                        item.status === "Failed" ? "text-error" : "text-outline"
                      }
                    />
                    <span className="font-mono text-data-mono text-on-surface truncate">
                      {item.filename}
                    </span>
                  </div>
                  <div className="col-span-3">
                    <span className="px-2 py-1 bg-surface-container-highest text-on-surface text-label-sm font-mono rounded-sm">
                      {item.contentType}
                    </span>
                  </div>
                  <div className="col-span-3 flex justify-end items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${styles.dot}`}
                    />
                    <span className={`text-label-caps ${styles.text}`}>
                      {item.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </div>

      {/* Right: Agent Loop Visualizer */}
      <div className="lg:col-span-4 flex flex-col gap-unit">
        <h2 className="text-headline-sm text-on-surface mb-4">
          Inference Loop Tracker
        </h2>
        <GlassCard className="p-6 h-[500px] flex flex-col">
          <div className="text-label-caps text-on-surface-variant mb-6 border-b border-outline-variant pb-2">
            {trace.loading
              ? "Active Trace: loading…"
              : trace.error
                ? `Active Trace: API error (${trace.error})`
                : !trace.data?.available
                  ? "Active Trace: (no trace events yet)"
                  : `Active Trace: ${trace.data.filename}`}
          </div>
          <div className="flex-1 relative flex flex-col justify-between pl-8">
            <div className="absolute left-[11px] top-4 bottom-4 w-px bg-outline-variant z-0" />
            {trace.data?.available
              ? trace.data.passes.map((p) => (
                  <LoopStep
                    key={p.pass}
                    label={PASS_LABELS[p.pass]}
                    done={p.state === "done"}
                    active={p.state === "active" || p.state === "failed"}
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
        </GlassCard>
      </div>

      {/* Bottom row: Cost + Quality */}
      <div className="lg:col-span-8 mt-4">
        <GlassCard className="p-6 flex flex-col justify-center">
          <div className="flex justify-between items-end mb-4">
            <div>
              <div className="text-label-caps text-on-surface-variant mb-1">
                Compute Cost Analysis
              </div>
              <div className="text-headline-lg text-primary">{fmtUSD(wafer)}</div>
              <div className="text-label-sm font-mono text-secondary mt-1">
                Wafer Local Inference
              </div>
            </div>
            <div className="text-right">
              <div className="text-headline-sm text-outline">{fmtUSD(gpt4)}</div>
              <div className="text-label-sm font-mono text-outline mt-1">
                GPT-4 Baseline Equivalent
              </div>
            </div>
          </div>
          <div className="w-full h-4 bg-surface-container-high rounded-full overflow-hidden flex relative">
            <div className="bg-outline-variant h-full opacity-30 absolute inset-0 w-full" />
            <div
              className="bg-secondary h-full relative z-10"
              style={{ width: `${Math.min(fillPct, 100)}%` }}
            />
          </div>
          <div className="text-right text-label-sm font-mono text-secondary mt-2 font-bold tracking-widest">
            {ratio !== null ? `~${Math.round(ratio)}× SAVINGS` : "—"}
          </div>
        </GlassCard>
      </div>

      <div className="lg:col-span-4 mt-4 grid grid-cols-2 gap-4">
        <QualityDial pct={interAgentPct} label="Inter-Agent\nAgreement" />
        <QualityDial pct={overallConfPct} label="Overall\nConfidence" />
      </div>
    </div>
  );
}

function LoopStep({
  done,
  active,
  muted,
  label,
  sub,
  children,
}: {
  done?: boolean;
  active?: boolean;
  muted?: boolean;
  label: string;
  sub?: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={`relative z-10 flex items-start gap-4 ${muted ? "opacity-50" : ""}`}
    >
      <div
        className={`w-6 h-6 rounded-full flex items-center justify-center mt-1 ${
          done
            ? "bg-secondary"
            : active
              ? "bg-surface border-2 border-secondary"
              : "bg-surface border-2 border-outline-variant"
        }`}
      >
        {done ? (
          <Icon name="check" className="text-[14px] text-on-secondary" />
        ) : active ? (
          <div className="w-2 h-2 rounded-full bg-secondary animate-flash" />
        ) : null}
      </div>
      <div className="w-full">
        <div
          className={`text-label-caps ${active ? "text-primary" : "text-on-surface"}`}
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

function QualityDial({ pct, label }: { pct: number; label: string }) {
  const dasharray = `${pct}, 100`;
  return (
    <GlassCard className="p-6 flex flex-col items-center justify-center text-center">
      <div className="relative w-20 h-20 mb-3 flex items-center justify-center">
        <svg className="w-full h-full -rotate-90 absolute" viewBox="0 0 36 36">
          <path
            className="text-surface-container-high"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
          />
          <path
            className="text-secondary"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="currentColor"
            strokeDasharray={dasharray}
            strokeWidth="3"
          />
        </svg>
        <span className="text-headline-sm text-on-surface">{pct}%</span>
      </div>
      <div className="text-label-caps text-on-surface-variant leading-tight whitespace-pre-line">
        {label}
      </div>
    </GlassCard>
  );
}
