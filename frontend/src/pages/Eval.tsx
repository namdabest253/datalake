import { Icon } from "@/components/Icon";
import { api, type EvalRecordView } from "@/api/client";
import { useApi } from "@/api/useApi";

export default function Eval() {
  const dims = useApi(() => api.evalDimensions(), []);
  const pair = useApi(() => api.evalPair(), []);
  const evalRows = dims.data ?? [];

  // Derived verdict: mean dimension delta (Datalake − GPT-4) across all dims.
  const meanDelta =
    pair.data && pair.data.available
      ? mean(
          Object.values(pair.data.dimension_scores)
            .map((p) => {
              const a = Number(p.A ?? p.a ?? 0);
              const b = Number(p.B ?? p.b ?? 0);
              return a - b; // sign already accounts for blinding via API de-blind
            })
            .filter((d) => Number.isFinite(d)),
        )
      : null;
  const verdictPct = meanDelta !== null ? Math.round(meanDelta * 20) : null; // 1–5 scale → ±100%

  // Total benchmarked queries = decided pair count, surfaced under the verdict.
  // We don't have it from the pair endpoint, so fall back to dimension sample count.
  const benchmarked = mostCommon(evalRows.map(() => 1)) ? evalRows.length : 0;

  const headerFile = pair.data?.available ? pair.data.filename : "—";
  const headerType =
    pair.data?.available && pair.data.datalake.content_type
      ? humanise(pair.data.datalake.content_type)
      : pair.data?.available
        ? "Unknown"
        : "—";

  return (
    <div className="grid grid-cols-12 gap-gutter content-start">
      {/* Document context */}
      <div className="col-span-12 bg-surface-container-lowest border border-outline-variant rounded-lg p-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-surface-container rounded">
            <Icon name="description" className="text-outline" />
          </div>
          <div>
            <p className="text-label-caps text-on-surface-variant">
              Evaluation Subject
            </p>
            <h3 className="text-headline-sm text-on-surface">{headerFile}</h3>
          </div>
        </div>
        <div className="flex gap-3">
          <Chip>{headerType}</Chip>
          {pair.data?.available && pair.data.judge_model && (
            <Chip>Judge: {pair.data.judge_model}</Chip>
          )}
        </div>
      </div>

      {pair.data && !pair.data.available && (
        <div className="col-span-12 bg-surface-container-lowest border border-outline-variant rounded-lg p-6 text-on-surface-variant text-label-caps">
          {pair.data.hint ?? "No eval pair yet. Run `datalake eval --n 200` to populate."}
        </div>
      )}

      {/* Side-by-side panels */}
      <div className="col-span-12 lg:col-span-6 flex flex-col gap-4">
        <RecordCard
          variant="baseline"
          title="GPT-4 Single Pass"
          caption="Baseline Model"
          icon="speed"
          loading={pair.loading}
          error={pair.error}
          record={pair.data?.available ? pair.data.gpt4 : null}
        />
      </div>

      <div className="col-span-12 lg:col-span-6 flex flex-col gap-4">
        <RecordCard
          variant="datalake"
          title="Datalake Agent Loop"
          caption="Inference Engine"
          icon="memory"
          loading={pair.loading}
          error={pair.error}
          record={pair.data?.available ? pair.data.datalake : null}
        />
      </div>

      {/* Verdict bar */}
      <div className="col-span-12 mt-2">
        <div className="bg-secondary text-on-secondary px-6 py-4 rounded-lg flex justify-between items-center shadow-float">
          <div className="flex items-center gap-4">
            <Icon name="verified" filled className="text-3xl" />
            <div>
              <h3 className="text-headline-md font-bold">
                {pair.data?.available && verdictPct !== null
                  ? pair.data.winner === "datalake"
                    ? `Datalake wins (${verdictPct > 0 ? "+" : ""}${verdictPct}% mean dim delta)`
                    : pair.data.winner === "gpt4"
                      ? `GPT-4 wins (${verdictPct}% mean dim delta)`
                      : "Tie"
                  : "Awaiting eval results"}
              </h3>
              <p className="text-label-caps text-on-secondary/80">
                {pair.data?.available && pair.data.rationale
                  ? pair.data.rationale.slice(0, 140) +
                    (pair.data.rationale.length > 140 ? "…" : "")
                  : evalRows.length
                    ? `${evalRows.length} dimension${evalRows.length === 1 ? "" : "s"} judged`
                    : "Run `datalake eval` to populate"}
              </p>
            </div>
          </div>
          <button className="bg-on-secondary text-secondary px-4 py-2 rounded text-label-caps font-bold hover:bg-surface-container-lowest transition-colors">
            View Full Logs
          </button>
        </div>
      </div>

      {/* Win rates */}
      <div className="col-span-12 mt-4 bg-surface-container-lowest border border-outline-variant rounded-lg p-6 shadow-sm">
        <h4 className="text-label-caps text-on-surface-variant mb-6 border-b border-outline-variant pb-2">
          Win Rates: Datalake vs Baseline ({benchmarked} dimension
          {benchmarked === 1 ? "" : "s"})
        </h4>
        <div className="space-y-6">
          {dims.loading && (
            <div className="text-on-surface-variant text-label-caps">Loading eval results…</div>
          )}
          {dims.error && (
            <div className="text-error text-label-caps">
              API error: {dims.error}. Is `datalake api` running?
            </div>
          )}
          {!dims.loading && !dims.error && evalRows.length === 0 && (
            <div className="text-on-surface-variant text-label-caps">
              No eval results yet. Run `datalake eval --n 200` to populate.
            </div>
          )}
          {evalRows.map((d) => (
            <div key={d.name}>
              <div className="flex justify-between font-mono text-data-mono mb-2">
                <span className="text-on-surface">{d.name}</span>
                <span className="text-secondary font-bold">
                  {d.winRate}% Win Rate
                </span>
              </div>
              <div className="w-full h-3 bg-surface-container rounded-full overflow-hidden flex">
                <div
                  className="h-full bg-secondary"
                  style={{ width: `${d.winRate}%` }}
                />
                <div
                  className="h-full bg-outline-variant"
                  style={{ width: `${100 - d.winRate}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-outline-variant/30 flex justify-end gap-4 text-label-sm font-mono text-outline">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-secondary" /> Datalake Win
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-outline-variant" /> Baseline
            Tie/Win
          </div>
        </div>
      </div>
    </div>
  );
}

function RecordCard({
  variant,
  title,
  caption,
  icon,
  loading,
  error,
  record,
}: {
  variant: "baseline" | "datalake";
  title: string;
  caption: string;
  icon: string;
  loading: boolean;
  error: string | null;
  record: EvalRecordView | null;
}) {
  const isDl = variant === "datalake";
  const accent = isDl ? "text-secondary" : "text-outline";
  const border = isDl ? "border-secondary/30" : "border-outline-variant";
  const topBar = isDl ? "bg-secondary-fixed" : "bg-outline-variant";
  return (
    <div
      className={`bg-surface-container-lowest border ${border} rounded-lg flex flex-col h-[500px] overflow-hidden shadow-sm relative`}
    >
      <div className={`absolute top-0 w-full h-1 ${topBar}`} />
      <div className="px-5 py-4 border-b border-outline-variant bg-surface-container/30 flex justify-between items-center">
        <div>
          <p className={`text-label-caps ${accent}`}>{caption}</p>
          <h4 className="text-headline-sm text-on-surface">{title}</h4>
        </div>
        <Icon name={icon} className={accent} />
      </div>
      <div className="p-5 overflow-y-auto flex-1 space-y-4">
        {loading && <p className="text-on-surface-variant text-label-caps">Loading…</p>}
        {error && (
          <p className="text-error text-label-caps">API error: {error}</p>
        )}
        {!loading && !error && !record && (
          <p className="text-on-surface-variant text-label-caps">
            No record. Run `datalake eval` to populate.
          </p>
        )}
        {record && (
          <>
            <div>
              <p className={`text-label-caps ${accent} mb-2`}>
                {isDl ? "Novelty Claim" : "Extracted Summary"}
              </p>
              <p
                className={`text-body-md text-on-surface bg-surface-container-low p-3 rounded border border-outline-variant/30 ${
                  isDl ? "" : "text-on-surface-variant"
                }`}
              >
                {isDl
                  ? record.novelty_claim || record.summary || "(empty)"
                  : record.summary || record.problem || "(empty)"}
              </p>
            </div>
            <div>
              <p className={`text-label-caps ${accent} mb-2`}>Methodology Tags</p>
              <div className="flex gap-2 flex-wrap">
                {record.methodology_named.length === 0 && !record.methodology_freetext ? (
                  <Tag>(none)</Tag>
                ) : (
                  <>
                    {record.methodology_named.map((m) =>
                      isDl ? <DataTag key={m}>{m}</DataTag> : <Tag key={m}>{m}</Tag>,
                    )}
                    {record.methodology_freetext && (
                      <Tag>{record.methodology_freetext.slice(0, 60)}</Tag>
                    )}
                  </>
                )}
              </div>
            </div>
            {isDl && record.claim_graph.length > 0 && (
              <div>
                <p className={`text-label-caps ${accent} mb-2`}>Claim Graph</p>
                <div className="space-y-2">
                  {record.claim_graph.slice(0, 3).map((c, i) => (
                    <div
                      key={i}
                      className="text-body-md text-on-surface bg-surface-container-low p-2 rounded border border-outline-variant/30"
                    >
                      <span className="font-mono text-label-sm text-outline">
                        claim:
                      </span>{" "}
                      {String((c as Record<string, unknown>).claim ?? "—")}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {!isDl && (
              <div className="mt-4 p-3 bg-error-container/20 border border-error/20 rounded flex gap-3">
                <Icon name="warning" className="text-error text-sm mt-0.5" />
                <p className="text-label-sm font-mono text-on-surface-variant">
                  Single-pass baseline; no critique step, no fan-out — methodology
                  detail and source attribution are intrinsically thinner.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

function mostCommon<T>(xs: T[]): boolean {
  return xs.length > 0;
}

function humanise(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="px-3 py-1 bg-surface-container-high text-on-surface-variant text-label-caps rounded border border-outline-variant/50">
      {children}
    </span>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-mono text-data-mono text-on-surface-variant bg-surface-container px-2 py-1 border border-outline-variant/30 rounded">
      {children}
    </span>
  );
}

function DataTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-mono text-data-mono text-secondary-fixed bg-primary-container px-2 py-1 border border-secondary/30 rounded">
      {children}
    </span>
  );
}
