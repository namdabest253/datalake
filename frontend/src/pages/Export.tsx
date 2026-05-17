import { Icon } from "@/components/Icon";
import { api } from "@/api/client";
import { useApi } from "@/api/useApi";

export default function ExportPage() {
  const sample = useApi(() => api.exportSample(), []);
  const counters = useApi(() => api.counters(), []);
  const text = sample.data?.sample ?? "";
  const hint = sample.data && !sample.data.available
    ? (sample.data as { hint?: string }).hint ?? "Run `datalake export` to generate the JSONL."
    : null;
  const docsTotal =
    (counters.data?.docs_done ?? 0) +
    (counters.data?.docs_partial ?? 0) +
    (counters.data?.docs_failed ?? 0);
  const confPct = Math.round((counters.data?.avg_overall_confidence ?? 0) * 100);
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-on-surface">Export Protocol</h1>
          <p className="text-body-md text-on-surface-variant mt-1">
            Finalize and distribute curated inference data.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <a
            href={api.exportDownloadUrl("csv")}
            download
            className="px-6 py-2 border border-outline bg-transparent text-on-surface hover:bg-surface-container-high transition-colors rounded flex items-center gap-2"
          >
            <Icon name="download" className="text-[18px]" />
            <span className="text-label-caps">Download Compliance CSV</span>
          </a>
          <button
            disabled
            title="Not yet wired — needs HF auth + datasets SDK integration."
            className="px-6 py-2 border border-outline bg-transparent text-on-surface-variant rounded flex items-center gap-2 opacity-50 cursor-not-allowed"
          >
            <Icon name="cloud_upload" className="text-[18px]" />
            <span className="text-label-caps">Push to Hugging Face Hub</span>
          </button>
          <a
            href={api.exportDownloadUrl("jsonl")}
            download
            className="px-8 py-2 bg-primary text-on-primary rounded hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm"
          >
            <Icon name="terminal" className="text-[18px]" />
            <span className="text-label-caps">Export JSONL</span>
          </a>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-gutter items-start">
        {/* JSONL preview */}
        <div className="col-span-12 xl:col-span-7">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm">
            <div className="bg-surface-container-low px-4 py-3 flex items-center justify-between border-b border-outline-variant">
              <div className="flex items-center gap-2">
                <Icon
                  name="code_blocks"
                  className="text-on-surface-variant text-[18px]"
                />
                <span className="text-label-caps text-on-surface">
                  sample_export_record.jsonl
                </span>
              </div>
              <button
                onClick={() => navigator.clipboard.writeText(text)}
                className="text-on-surface-variant hover:text-on-surface"
                disabled={!text}
              >
                <Icon name="content_copy" className="text-[18px]" />
              </button>
            </div>
            <pre className="p-6 bg-inverse-surface text-inverse-on-surface overflow-x-auto font-mono text-data-mono leading-relaxed max-h-[480px]">
              <code>
                {sample.loading
                  ? "Loading sample…"
                  : sample.error
                    ? `API error: ${sample.error}. Is \`datalake api\` running?`
                    : text || hint || ""}
              </code>
            </pre>
          </div>
        </div>

        {/* Dataset card */}
        <div className="col-span-12 xl:col-span-5">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col gap-6">
            <div className="flex items-center gap-3 border-b border-outline-variant pb-4">
              <div className="w-10 h-10 rounded bg-primary-container text-on-primary-container flex items-center justify-center">
                <Icon name="description" filled />
              </div>
              <div>
                <h2 className="text-headline-sm text-on-surface">
                  Dataset Card Preview
                </h2>
                <p className="text-label-caps text-on-surface-variant">
                  Auto-generated Markdown Documentation
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <StatCard
                icon="inventory_2"
                label="CORPUS VOLUME"
                value={docsTotal.toLocaleString()}
                sub={
                  counters.data
                    ? `${counters.data.docs_done} done · ${counters.data.docs_partial} partial · ${counters.data.docs_failed} failed`
                    : "Loading…"
                }
              />
              <StatCard
                icon="payments"
                label="WAFER SPEND"
                valueClassName="text-body-lg font-semibold leading-tight"
                value={
                  counters.data ? `$${counters.data.wafer_usd.toFixed(4)}` : "—"
                }
                sub={
                  counters.data?.cost_ratio_vs_gpt4
                    ? `${Math.round(counters.data.cost_ratio_vs_gpt4)}× cheaper than GPT-4`
                    : "—"
                }
              />
              <div className="col-span-2 bg-surface-container px-4 py-4 rounded-lg border border-outline-variant/50 flex items-center justify-between">
                <div>
                  <span className="text-label-sm font-mono text-on-surface-variant flex items-center gap-1 mb-1">
                    <Icon name="verified_user" className="text-[14px]" />
                    QUALITY ASSURANCE
                  </span>
                  <div className="text-body-md text-on-surface">
                    Avg Overall Confidence
                  </div>
                </div>
                <div className="text-headline-lg text-secondary flex items-center gap-2">
                  {confPct}%
                  <Icon name="check_circle" filled className="text-secondary" />
                </div>
              </div>
            </div>

            <p className="text-body-md text-on-surface-variant leading-relaxed">
              <a
                href={api.exportDownloadUrl("card")}
                download
                className="text-primary hover:text-secondary underline"
              >
                Download the auto-generated dataset_card.md
              </a>{" "}
              for full provenance, methodology, and the GPT-4 cost comparison.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  sub,
  valueClassName,
}: {
  icon: string;
  label: string;
  value: string;
  sub: string;
  valueClassName?: string;
}) {
  return (
    <div className="bg-surface-container px-4 py-4 rounded-lg border border-outline-variant/50">
      <span className="text-label-sm font-mono text-on-surface-variant flex items-center gap-1 mb-2">
        <Icon name={icon} className="text-[14px]" />
        {label}
      </span>
      <div className={valueClassName ?? "text-headline-md text-on-surface"}>
        {value}
      </div>
      <span className="font-mono text-on-surface-variant text-[11px]">
        {sub}
      </span>
    </div>
  );
}
