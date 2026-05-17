import { Icon } from "@/components/Icon";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/api/client";
import { useApi } from "@/api/useApi";

// Material-ish palette for bar chart; cycles if there are more formats than colours.
const BAR_PALETTE = ["bg-secondary", "bg-primary", "bg-outline", "bg-error"];

export default function Ingestion() {
  const uploads = useApi(() => api.recentUploads(), []);
  const formats = useApi(() => api.formatDistribution(), []);
  const rows = uploads.data ?? [];
  const formatBars = (formats.data ?? []).slice(0, 4);
  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h2 className="text-headline-lg text-on-surface">Ingestion Hub</h2>
          <p className="text-body-md text-on-surface-variant mt-1">
            Upload and stage data for inference pipelines.
          </p>
        </div>
        <button className="bg-secondary text-on-secondary px-6 py-3 rounded text-label-caps shadow-sm hover:opacity-90 transition-opacity flex items-center gap-2">
          <Icon name="hub" />
          Start Multi-Pass Agent Loop
        </button>
      </div>

      {/* Drag & drop */}
      <div className="w-full border-2 border-dashed border-outline-variant bg-surface-container-low rounded-xl p-12 flex flex-col items-center justify-center text-center transition-colors hover:border-secondary hover:bg-surface-container cursor-pointer">
        <div className="bg-surface-container-highest p-4 rounded-full mb-4">
          <Icon name="cloud_upload" className="text-4xl text-on-surface-variant" />
        </div>
        <h3 className="text-headline-sm text-on-surface mb-2">
          Drag & Drop Folder
        </h3>
        <p className="text-body-md text-on-surface-variant mb-6 max-w-md">
          Supported formats: ZIP, Folder structures, CSV, JSON, PDF. Max batch
          size: 50 GB.
        </p>
        <button className="border border-outline bg-surface-container-lowest px-6 py-2 rounded text-label-caps text-on-surface hover:bg-surface-container-highest transition-colors">
          Browse Files
        </button>
      </div>

      {/* Stats + Recent uploads */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <GlassCard className="p-6 flex flex-col">
          <span className="text-label-caps text-on-surface-variant mb-2 flex items-center gap-2">
            <Icon name="pie_chart" className="text-[16px]" />
            Initial Parsing Stats
          </span>
          <div className="flex-1 flex items-end gap-6 mt-4">
            {formats.loading && (
              <span className="text-on-surface-variant text-label-caps">Loading…</span>
            )}
            {formats.error && (
              <span className="text-error text-label-caps">
                API error: {formats.error}
              </span>
            )}
            {!formats.loading && !formats.error && formatBars.length === 0 && (
              <span className="text-on-surface-variant text-label-caps">
                No documents ingested yet.
              </span>
            )}
            {formatBars.map((bar, i) => (
              <div
                key={bar.label}
                className="flex flex-col items-center gap-2 flex-1"
              >
                <div className="w-full h-24 bg-surface-container-highest rounded-t relative overflow-hidden flex items-end justify-center">
                  <div
                    className={`w-full ${BAR_PALETTE[i % BAR_PALETTE.length]} absolute bottom-0 transition-all duration-500`}
                    style={{ height: `${bar.pct}%` }}
                  />
                </div>
                <span className="font-mono text-data-mono text-on-surface text-center">
                  {bar.pct}% {bar.label}
                </span>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard className="p-6 flex flex-col justify-between col-span-1 md:col-span-2">
          <h3 className="text-headline-sm text-on-surface mb-4">
            Recent Uploads
          </h3>
          <div className="w-full overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-outline-variant text-label-caps text-on-surface-variant">
                  <th className="py-2 px-4 font-normal">Source Name</th>
                  <th className="py-2 px-4 font-normal text-right">
                    File Count
                  </th>
                  <th className="py-2 px-4 font-normal w-1/3">Status</th>
                  <th className="py-2 px-4 font-normal text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="text-body-md text-on-surface">
                {uploads.loading && (
                  <tr>
                    <td colSpan={4} className="py-4 px-4 text-on-surface-variant text-label-caps">
                      Loading recent runs…
                    </td>
                  </tr>
                )}
                {uploads.error && (
                  <tr>
                    <td colSpan={4} className="py-4 px-4 text-error text-label-caps">
                      API error: {uploads.error}. Is `datalake api` running?
                    </td>
                  </tr>
                )}
                {!uploads.loading && !uploads.error && rows.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-4 px-4 text-on-surface-variant text-label-caps">
                      No ingestion runs yet.
                    </td>
                  </tr>
                )}
                {rows.map((u) => (
                  <tr
                    key={u.id}
                    className="border-b border-outline-variant/30 row-data"
                  >
                    <td className="py-3 px-4 font-mono text-data-mono flex items-center gap-2">
                      <Icon
                        name={u.iconName}
                        className="text-on-surface-variant text-[18px]"
                      />
                      {u.name}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-data-mono">
                      {u.files.toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      {u.status === "Processing" ? (
                        <>
                          <div className="flex items-center gap-3">
                            <div className="flex-1 h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                              <div
                                className="h-full bg-secondary rounded-full"
                                style={{ width: `${u.progress}%` }}
                              />
                            </div>
                            <span className="font-mono text-data-mono text-secondary">
                              {u.progress}%
                            </span>
                          </div>
                          <span className="text-label-sm font-mono text-on-surface-variant mt-1 block">
                            Processing...
                          </span>
                        </>
                      ) : (
                        <div className="flex items-center gap-2 text-secondary">
                          <Icon name="check_circle" className="text-[16px]" />
                          <span className="text-label-caps">Completed</span>
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button className="text-on-surface-variant hover:text-primary transition-colors">
                        <Icon name="more_horiz" className="text-[20px]" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
