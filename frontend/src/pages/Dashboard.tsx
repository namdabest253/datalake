import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { GlassCard } from "@/components/GlassCard";
import { LoopTracker } from "@/components/LoopTracker";
import { api } from "@/api/client";
import { useApi } from "@/api/useApi";

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
  const stream = useApi(() => api.stream(undefined, 20), [], { cacheKey: "dashboard:stream" });
  const counters = useApi(() => api.counters(), [], { cacheKey: "dashboard:counters" });
  const trace = useApi(() => api.activeTrace(), [], { cacheKey: "dashboard:activeTrace" });
  const traces = useApi(() => api.activeTraces(), [], { cacheKey: "dashboard:activeTraces" });

  // Cost-bar fill is wafer/gpt4 ratio expressed as percentage of the GPT-4 bar.
  const wafer = counters.data?.wafer_usd ?? 0;
  const gpt4 = counters.data?.gpt4_equivalent_usd ?? 0;
  const ratio = counters.data?.cost_ratio_vs_gpt4 ?? null;
  const fillPct = gpt4 > 0 ? Math.max(0.5, (wafer / gpt4) * 100) : 0;
  const items = stream.data ?? [];
  const overallConfPct = Math.round((counters.data?.avg_overall_confidence ?? 0) * 100);
  // Median per-call output throughput from /api/active-traces. Dial fill scales to
  // 100 tok/s = full so the visual still says something at typical Wafer rates.
  const tps = traces.data?.metrics?.tokens_per_sec ?? 0;
  const tpsFill = Math.min(100, Math.round(tps));

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
          <LoopTracker
            trace={trace.data}
            loading={trace.loading}
            error={trace.error}
          />
        </GlassCard>
      </div>

      {/* Bottom row: Cost + Quality */}
      <div className="lg:col-span-8 mt-4 relative z-30">
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
              <div className="text-label-sm font-mono text-outline mt-1 flex items-center justify-end gap-1">
                GPT-4 Baseline Equivalent
                <span
                  tabIndex={0}
                  aria-label="How the GPT-4 baseline is estimated"
                  className="relative group text-outline hover:text-on-surface focus:text-on-surface cursor-help outline-none"
                >
                  <Icon name="info" className="text-[14px]" />
                  <BaselineEquivalentPopover />
                </span>
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
        <QualityDial
          pct={tpsFill}
          display={
            <span className="text-body-lg font-semibold">
              {tps.toFixed(1)}
              <br />
              tok/s
            </span>
          }
          label="Inference Throughput"
        />
        <QualityDial pct={overallConfPct} label="Overall Confidence" />
      </div>
    </div>
  );
}

function BaselineEquivalentPopover() {
  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute left-full top-1/2 -translate-y-[65%] ml-2 w-96 p-4 z-50 rounded-lg border border-outline-variant bg-surface-container-lowest shadow-float text-left whitespace-normal opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-150 normal-case font-sans"
    >
      <p className="text-label-caps text-on-surface mb-2">
        How this is estimated
      </p>
      <p className="text-body-sm text-on-surface-variant mb-3 leading-relaxed">
        For every Wafer call the agent loop actually makes, we insert a
        parallel &quot;foil&quot; row that re-prices the exact same{" "}
        <span className="text-on-surface font-mono">(tokens_in, tokens_out)</span>{" "}
        at GPT-4 Turbo&apos;s published rates. No GPT-4 call is made —
        it&apos;s a counterfactual on observed token counts.
      </p>
      <p className="text-label-caps text-on-surface-variant mb-1">
        GPT-4 Turbo pricing
      </p>
      <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 text-body-sm font-mono mb-3">
        <div className="contents">
          <dt className="text-on-surface-variant">Input</dt>
          <dd className="text-on-surface text-right">$10.00 / 1M tok</dd>
        </div>
        <div className="contents">
          <dt className="text-on-surface-variant">Output</dt>
          <dd className="text-on-surface text-right">$30.00 / 1M tok</dd>
        </div>
      </dl>
      <p className="text-body-sm text-on-surface-variant mb-3 leading-relaxed">
        Summed across the run, this is what the same 11-call agent loop
        would have cost if every call had hit GPT-4 instead of Wafer-hosted
        Qwen. The ratio against actual Wafer spend gives the savings
        figure.
      </p>
      <p className="text-label-sm text-outline italic">
        Token counts taken from the provider&apos;s reported usage where
        available, else a local tiktoken estimate.
      </p>
    </div>
  );
}

function QualityDial({
  pct,
  label,
  display,
}: {
  pct: number;
  label: string;
  display?: ReactNode;
}) {
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
        <span className="text-headline-sm text-on-surface leading-tight text-center">
          {display ?? `${pct}%`}
        </span>
      </div>
      <div className="text-label-caps text-on-surface-variant leading-tight whitespace-pre-line">
        {label}
      </div>
    </GlassCard>
  );
}
