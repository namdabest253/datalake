import { Icon } from "@/components/Icon";
import { type ComplianceStatus } from "@/data/mock";
import { api } from "@/api/client";
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

export default function Catalog() {
  const catalog = useApi(() => api.catalog(undefined, { limit: 500 }), []);
  const rows = catalog.data ?? [];
  const licenseReady = rows.filter(
    (r) => r.score >= 70 && (r.compliance === "clean" || r.compliance === "unclear"),
  ).length;
  // Per-doc midpoint commercial value — same constants as the Streamlit panel.
  const estMarketValue = rows
    .filter((r) => r.compliance !== "restricted")
    .reduce((acc, r) => acc + (r.score >= 70 ? 800 : 200), 0);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-headline-lg text-on-surface">
        Catalog & Compliance
      </h1>

      {/* Search + filters */}
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center w-full">
        <div className="relative w-full md:w-96">
          <Icon
            name="search"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-outline"
          />
          <input
            type="text"
            placeholder="Search papers, grants, or PIs..."
            className="w-full bg-surface-container-lowest border border-outline-variant rounded pl-10 pr-4 py-2 text-body-md text-on-surface placeholder-outline focus:ring-2 focus:ring-secondary focus:border-secondary transition-all outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <FilterPill icon="check_circle" label="License-Ready" active />
          <FilterPill icon="lock" label="HIPAA-Restricted" />
          <FilterPill icon="article" label="Research Papers" />
          <FilterPill icon="trending_up" label="High Commercial Score" />
        </div>
      </div>

      {/* Summary */}
      <div className="bg-surface-container-lowest/80 backdrop-blur-glass border border-outline-variant/50 rounded-lg p-6 flex flex-col md:flex-row justify-between items-center shadow-glass-sm">
        <div>
          <h3 className="text-label-caps text-on-surface-variant mb-1">
            Sellable Subset
          </h3>
          <p className="text-headline-md text-on-surface flex items-center gap-2">
            <span className="text-secondary font-mono">{licenseReady.toLocaleString()}</span>
            Documents Licensed-Ready
          </p>
        </div>
        <div className="mt-4 md:mt-0 text-right border-t md:border-t-0 md:border-l border-outline-variant/30 pt-4 md:pt-0 md:pl-6 w-full md:w-auto">
          <p className="text-label-caps text-on-surface-variant mb-1">
            Est. Market Value
          </p>
          <p className="text-headline-sm text-secondary font-mono">${estMarketValue.toLocaleString()}</p>
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
              {!catalog.loading && !catalog.error && rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-on-surface-variant text-label-caps">
                    No catalog records yet. Run `datalake run` to populate.
                  </td>
                </tr>
              )}
              {rows.map((row) => {
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
                      <button className="text-label-caps text-primary hover:text-secondary transition-colors">
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
            Showing 1–{rows.length} of {rows.length}
          </span>
          <div className="flex items-center gap-2">
            <button
              className="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors disabled:opacity-40"
              disabled
            >
              <Icon name="chevron_left" className="text-[20px]" />
            </button>
            <button className="p-1 rounded text-on-surface hover:bg-surface-container-high transition-colors">
              <Icon name="chevron_right" className="text-[20px]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function FilterPill({
  icon,
  label,
  active,
}: {
  icon: string;
  label: string;
  active?: boolean;
}) {
  return (
    <button
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
