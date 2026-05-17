import { useMemo, useState } from "react";
import { Icon } from "@/components/Icon";
import { type ComplianceStatus } from "@/data/mock";
import { api, type DocumentDetail } from "@/api/client";
import { useApi } from "@/api/useApi";

const COMPLIANCE_STYLES: Record<
  ComplianceStatus,
  { bg: string; border: string; text: string; icon: string }
> = {
  clean: {
    bg: "bg-secondary-container/30",
    border: "border-secondary/20",
    text: "text-secondary",
    icon: "verified",
  },
  restricted: {
    bg: "bg-error-container/50",
    border: "border-error/20",
    text: "text-error",
    icon: "warning",
  },
  unclear: {
    bg: "bg-surface-container-high",
    border: "border-outline-variant",
    text: "text-on-surface-variant",
    icon: "help",
  },
};

const PAGE_SIZE = 25;

// Filter pills. Each pill is a predicate over a CatalogRow plus a UI label/icon.
// Pills are independently toggleable; rows must match ALL active pills (AND).
type CatalogRow = {
  id: string;
  name: string;
  owner: string;
  compliance: string;
  complianceLabel: string;
  score: number;
  iconName: string;
};

type Pill = {
  key: string;
  icon: string;
  label: string;
  test: (r: CatalogRow) => boolean;
};

const PILLS: Pill[] = [
  {
    key: "license-ready",
    icon: "check_circle",
    label: "License-Ready",
    test: (r) => r.compliance === "clean" && r.score >= 70,
  },
  {
    key: "restricted",
    icon: "lock",
    label: "Restricted",
    test: (r) => r.compliance === "restricted",
  },
  {
    key: "research-paper",
    icon: "article",
    label: "Research Papers",
    test: (r) => r.iconName === "description" || r.iconName === "article",
  },
  {
    key: "high-score",
    icon: "trending_up",
    label: "High Commercial Score",
    test: (r) => r.score >= 80,
  },
];

export default function Catalog() {
  const catalog = useApi(() => api.catalog(undefined, { limit: 500 }), []);
  const rows = catalog.data ?? [];

  const [search, setSearch] = useState("");
  const [activePills, setActivePills] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(0);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  // Apply search + pill filters together. The .toLowerCase() check covers both
  // the document name and the owner string so users can search by either.
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((r) => {
      if (q && !`${r.name} ${r.owner}`.toLowerCase().includes(q)) return false;
      for (const pillKey of activePills) {
        const pill = PILLS.find((p) => p.key === pillKey);
        if (pill && !pill.test(r)) return false;
      }
      return true;
    });
  }, [rows, search, activePills]);

  // Reset page when filters change so the user lands on page 1.
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  const licenseReady = filtered.filter(
    (r) => r.score >= 70 && (r.compliance === "clean" || r.compliance === "unclear"),
  ).length;
  const estMarketValue = filtered
    .filter((r) => r.compliance !== "restricted")
    .reduce((acc, r) => acc + (r.score >= 70 ? 800 : 200), 0);

  const togglePill = (key: string) => {
    setActivePills((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
    setPage(0);
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-headline-lg text-on-surface">Catalog & Compliance</h1>

      {/* Search + filters */}
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center w-full">
        <div className="relative w-full md:w-96">
          <Icon
            name="search"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-outline"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            placeholder="Search by document name or owner..."
            className="w-full bg-surface-container-lowest border border-outline-variant rounded pl-10 pr-4 py-2 text-body-md text-on-surface placeholder-outline focus:ring-2 focus:ring-secondary focus:border-secondary transition-all outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {PILLS.map((p) => (
            <FilterPill
              key={p.key}
              icon={p.icon}
              label={p.label}
              active={activePills.has(p.key)}
              onClick={() => togglePill(p.key)}
            />
          ))}
        </div>
      </div>

      {/* Summary — reflects FILTERED set so the numbers move as you toggle */}
      <div className="bg-surface-container-lowest/80 backdrop-blur-glass border border-outline-variant/50 rounded-lg p-6 flex flex-col md:flex-row justify-between items-center shadow-glass-sm">
        <div>
          <h3 className="text-label-caps text-on-surface-variant mb-1">
            Sellable Subset (filtered)
          </h3>
          <p className="text-headline-md text-on-surface flex items-center gap-2">
            <span className="text-secondary font-mono">
              {licenseReady.toLocaleString()}
            </span>
            Documents Licensed-Ready
          </p>
        </div>
        <div className="mt-4 md:mt-0 text-right border-t md:border-t-0 md:border-l border-outline-variant/30 pt-4 md:pt-0 md:pl-6 w-full md:w-auto">
          <p className="text-label-caps text-on-surface-variant mb-1">
            Est. Market Value
          </p>
          <p className="text-headline-sm text-secondary font-mono">
            ${estMarketValue.toLocaleString()}
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden flex-1 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead>
              <tr className="bg-surface-container border-b border-outline-variant">
                <th className="p-3 text-label-caps text-on-surface-variant whitespace-nowrap">
                  Document Name
                </th>
                <th className="p-3 text-label-caps text-on-surface-variant whitespace-nowrap">
                  Ownership
                </th>
                <th className="p-3 text-label-caps text-on-surface-variant whitespace-nowrap">
                  Compliance
                </th>
                <th className="p-3 text-label-caps text-on-surface-variant whitespace-nowrap">
                  Commercial Score
                </th>
                <th className="p-3 text-label-caps text-on-surface-variant whitespace-nowrap text-right">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="text-body-md text-on-surface">
              {catalog.loading && (
                <tr>
                  <td colSpan={5} className="p-6 text-on-surface-variant text-label-caps">
                    Loading catalog…
                  </td>
                </tr>
              )}
              {catalog.error && (
                <tr>
                  <td colSpan={5} className="p-6 text-error text-label-caps">
                    API error: {catalog.error}. Is `datalake api` running?
                  </td>
                </tr>
              )}
              {!catalog.loading && !catalog.error && filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-on-surface-variant text-label-caps">
                    {rows.length === 0
                      ? "No catalog records yet. Run `datalake run` to populate."
                      : "No records match the current filters."}
                  </td>
                </tr>
              )}
              {pageRows.map((row) => {
                const cs = COMPLIANCE_STYLES[row.compliance as ComplianceStatus];
                return (
                  <tr
                    key={row.id}
                    className="border-b border-outline-variant/30 row-data h-10"
                  >
                    <td className="p-3 font-medium">
                      <span className="flex items-center gap-2">
                        <Icon
                          name={row.iconName}
                          className="text-outline text-[18px]"
                        />
                        {row.name}
                      </span>
                    </td>
                    <td className="p-3 text-on-surface-variant">{row.owner}</td>
                    <td className="p-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-label-sm font-mono ${cs.bg} ${cs.text} border ${cs.border}`}
                      >
                        <Icon name={cs.icon} className="text-[14px]" />
                        {row.complianceLabel}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-mono w-8 text-right ${row.score >= 80 ? "text-secondary" : "text-on-surface-variant"}`}
                        >
                          {row.score}
                        </span>
                        <div className="w-24 h-1.5 bg-surface-container-high rounded-full overflow-hidden">
                          <div
                            className={`h-full ${row.score >= 80 ? "bg-secondary" : "bg-outline-variant"}`}
                            style={{ width: `${row.score}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => setSelectedDocId(row.id)}
                        className="text-label-caps text-primary hover:text-secondary transition-colors"
                      >
                        View Labels
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="bg-surface-container-lowest border-t border-outline-variant p-3 flex justify-between items-center">
          <span className="text-label-sm font-mono text-on-surface-variant">
            {filtered.length === 0
              ? "0 records"
              : `Showing ${safePage * PAGE_SIZE + 1}–${Math.min(
                  (safePage + 1) * PAGE_SIZE,
                  filtered.length,
                )} of ${filtered.length}`}
            {rows.length !== filtered.length && (
              <span className="text-outline ml-2">
                (filtered from {rows.length})
              </span>
            )}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={safePage <= 0}
              className="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Icon name="chevron_left" className="text-[20px]" />
            </button>
            <span className="font-mono text-label-sm text-on-surface-variant">
              {safePage + 1} / {pageCount}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
              disabled={safePage >= pageCount - 1}
              className="p-1 rounded text-on-surface hover:bg-surface-container-high transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Icon name="chevron_right" className="text-[20px]" />
            </button>
          </div>
        </div>
      </div>

      {selectedDocId && (
        <LabelModal docId={selectedDocId} onClose={() => setSelectedDocId(null)} />
      )}
    </div>
  );
}

function FilterPill({
  icon,
  label,
  active,
  onClick,
}: {
  icon: string;
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full border text-label-caps flex items-center gap-1 transition-colors ${
        active
          ? "border-secondary text-secondary bg-secondary/10 hover:bg-secondary/20"
          : "border-outline-variant text-on-surface-variant bg-surface-container-lowest hover:bg-surface-container-high"
      }`}
    >
      <Icon name={icon} className="text-[16px]" />
      {label}
    </button>
  );
}

function LabelModal({ docId, onClose }: { docId: string; onClose: () => void }) {
  const detail = useApi(() => api.document(docId), [docId]);
  const doc = detail.data?.document;
  const catalog = detail.data?.catalog;
  const label = detail.data?.label;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-scrim/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-surface-container-lowest border border-outline-variant rounded-xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col shadow-float"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant">
          <div className="min-w-0">
            <p className="text-label-caps text-on-surface-variant">
              Document Detail
            </p>
            <h2 className="text-headline-sm text-on-surface truncate">
              {doc?.source_path ?? "Loading…"}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded hover:bg-surface-container-high transition-colors text-on-surface-variant"
            aria-label="Close"
          >
            <Icon name="close" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {detail.loading && (
            <p className="text-on-surface-variant text-label-caps">
              Loading document…
            </p>
          )}
          {detail.error && (
            <p className="text-error text-label-caps">
              API error: {detail.error}
            </p>
          )}

          {catalog && <CatalogBlock catalog={catalog} />}

          {label ? (
            <LabelBlock label={label} />
          ) : (
            !detail.loading &&
            !detail.error && (
              <p className="text-on-surface-variant text-label-caps">
                No label payload for this document.
              </p>
            )
          )}
        </div>
      </div>
    </div>
  );
}

function CatalogBlock({
  catalog,
}: {
  catalog: NonNullable<DocumentDetail["catalog"]>;
}) {
  return (
    <section>
      <h3 className="text-label-caps text-on-surface-variant mb-3">Catalog</h3>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-body-md">
        <DLine k="Content type" v={`${catalog.content_type} (${(catalog.content_type_confidence * 100).toFixed(0)}%)`} />
        <DLine k="Ownership" v={`${catalog.ownership} (${(catalog.ownership_confidence * 100).toFixed(0)}%)`} />
        <DLine k="Commercial score" v={String(catalog.commercial_score)} />
        <DLine k="Commercial action" v={catalog.commercial_action} />
        <DLine k="Compliance flags" v={catalog.compliance_flags.join(", ") || "—"} />
      </dl>
      <p className="mt-3 text-body-md text-on-surface-variant border-l-2 border-outline-variant pl-3">
        <span className="text-label-caps text-on-surface-variant block mb-1">
          Ownership rationale
        </span>
        {catalog.ownership_rationale}
      </p>
    </section>
  );
}

function LabelBlock({
  label,
}: {
  label: NonNullable<DocumentDetail["label"]>;
}) {
  const named = label.methodology.named ?? [];
  return (
    <section className="space-y-4">
      <h3 className="text-label-caps text-on-surface-variant">Label</h3>
      <div>
        <p className="text-label-caps text-secondary mb-1">Novelty claim</p>
        <p className="text-body-md text-on-surface bg-surface-container-low p-3 rounded border border-outline-variant/30">
          {label.novelty_claim || "(empty)"}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-label-caps text-on-surface-variant mb-1">
            Methodology
          </p>
          <div className="flex flex-wrap gap-1">
            {named.length === 0 && !label.methodology.other_freetext ? (
              <span className="text-body-md text-on-surface-variant">(none)</span>
            ) : (
              <>
                {named.map((m) => (
                  <span
                    key={m}
                    className="font-mono text-data-mono text-on-surface bg-surface-container px-2 py-1 border border-outline-variant/30 rounded"
                  >
                    {m}
                  </span>
                ))}
                {label.methodology.other_freetext && (
                  <span className="text-body-md text-on-surface-variant ml-2">
                    + {label.methodology.other_freetext}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
        <div>
          <p className="text-label-caps text-on-surface-variant mb-1">
            Domain tags
          </p>
          <div className="flex flex-wrap gap-1">
            {label.domain_tags.length === 0 ? (
              <span className="text-body-md text-on-surface-variant">(none)</span>
            ) : (
              label.domain_tags.map((t) => (
                <span
                  key={t}
                  className="font-mono text-data-mono text-secondary-fixed bg-primary-container px-2 py-1 border border-secondary/30 rounded"
                >
                  {t}
                </span>
              ))
            )}
          </div>
        </div>
      </div>
      {Object.keys(label.structured_abstract).length > 0 && (
        <div>
          <p className="text-label-caps text-on-surface-variant mb-2">
            Structured abstract
          </p>
          <dl className="space-y-2 text-body-md">
            {Object.entries(label.structured_abstract).map(([k, v]) => (
              <div key={k}>
                <dt className="text-label-caps text-outline mb-0.5">{k}</dt>
                <dd className="text-on-surface">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
      {label.claim_graph.length > 0 && (
        <div>
          <p className="text-label-caps text-on-surface-variant mb-2">
            Claim graph ({label.claim_graph.length})
          </p>
          <ul className="space-y-1 text-body-md">
            {label.claim_graph.slice(0, 5).map((c, i) => (
              <li
                key={i}
                className="bg-surface-container-low border border-outline-variant/30 rounded p-2"
              >
                {String((c as Record<string, unknown>).claim ?? JSON.stringify(c))}
              </li>
            ))}
          </ul>
        </div>
      )}
      {label.citations.length > 0 && (
        <p className="text-label-sm font-mono text-on-surface-variant">
          {label.citations.length} citations parsed
        </p>
      )}
    </section>
  );
}

function DLine({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="text-label-caps text-on-surface-variant">{k}</dt>
      <dd className="text-on-surface font-mono text-data-mono break-words">{v}</dd>
    </>
  );
}
