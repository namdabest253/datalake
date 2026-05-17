import { Icon } from "@/components/Icon";
import { api } from "@/api/client";
import { useApi } from "@/api/useApi";

function fmtUSD(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(2)}K`;
  if (n >= 1) return `$${n.toFixed(2)}`;
  return `$${n.toFixed(4)}`;
}

function fmtCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export function TopBar() {
  // Single fetch shared across every /app/* page. Re-runs on mount per page nav.
  const counters = useApi(() => api.counters(), []);
  const docs = counters.data?.docs_done ?? 0;
  const wafer = counters.data?.wafer_usd ?? 0;
  const ratio = counters.data?.cost_ratio_vs_gpt4 ?? null;
  const totalDocs = counters.loading ? "—" : `Total: ${fmtCount(docs)}`;
  // No live throughput at this tier (Wafer serialises calls), so surface cumulative
  // Wafer spend instead — that's the metric the demo claim actually rides on.
  const spendLabel = counters.loading
    ? "—"
    : ratio !== null
      ? `${fmtUSD(wafer)} · ${Math.round(ratio)}× vs GPT-4`
      : fmtUSD(wafer);

  return (
    <header className="flex justify-between items-center h-14 px-margin-desktop bg-surface/80 backdrop-blur-glass border-b border-outline-variant shadow-sm fixed top-0 right-0 w-full md:w-[calc(100%-240px)] z-40">
      <div className="flex items-center gap-4">
        <h2 className="hidden md:block text-headline-sm font-bold tracking-tighter text-on-surface">
          DATALAKE
        </h2>
      </div>
      <div className="flex items-center gap-6">
        <div className="hidden lg:flex items-center gap-4 border-r border-outline-variant pr-6">
          <div className="flex flex-col items-end">
            <span className="text-label-caps text-on-surface-variant">
              Wafer Spend
            </span>
            <span className="font-mono text-data-mono text-primary animate-flash">
              {spendLabel}
            </span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-label-caps text-on-surface-variant">
              Total Processed
            </span>
            <span className="font-mono text-data-mono text-primary">
              {totalDocs}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-on-surface-variant">
          <span
            className={`p-2 rounded flex items-center ${
              counters.error ? "text-error" : "text-secondary animate-flash"
            }`}
            title={
              counters.loading
                ? "API connection: loading…"
                : counters.error
                  ? `API connection: ${counters.error}`
                  : "API connection: live"
            }
          >
            <Icon name="sensors" filled={!counters.error} />
          </span>
        </div>
      </div>
    </header>
  );
}
