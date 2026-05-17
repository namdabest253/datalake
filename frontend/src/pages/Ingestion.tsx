import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "@/components/Icon";
import { GlassCard } from "@/components/GlassCard";
import { api, type UploadResult } from "@/api/client";
import { useApi } from "@/api/useApi";

const ACCEPTED_SUFFIXES = [".pdf", ".txt", ".md", ".json"];

// Material-ish palette for bar chart; cycles if there are more formats than colours.
const BAR_PALETTE = ["bg-secondary", "bg-primary", "bg-outline", "bg-error"];

export default function Ingestion() {
  const [refreshTick, setRefreshTick] = useState(0);
  const uploads = useApi(() => api.recentUploads(), [refreshTick]);
  const formats = useApi(() => api.formatDistribution(), []);
  const rows = uploads.data ?? [];
  const formatBars = (formats.data ?? []).slice(0, 4);

  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const navigate = useNavigate();
  const menuRootRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Close the dropdown on any outside click or Escape.
  useEffect(() => {
    if (openMenu === null) return;
    const onDown = (e: MouseEvent) => {
      if (!menuRootRef.current?.contains(e.target as Node)) setOpenMenu(null);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenMenu(null);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [openMenu]);

  const handleView = (runId: string) => {
    setOpenMenu(null);
    navigate(`/app/catalog?run_id=${encodeURIComponent(runId)}`);
  };

  const handleCopy = async (runId: string) => {
    setOpenMenu(null);
    try {
      await navigator.clipboard.writeText(runId);
      setCopiedId(runId);
      setTimeout(() => setCopiedId((c) => (c === runId ? null : c)), 1500);
    } catch {
      // Clipboard can be blocked in insecure contexts; fall back silently.
    }
  };

  const uploadFiles = async (files: File[]) => {
    if (files.length === 0) return;
    const eligible = files.filter((f) =>
      ACCEPTED_SUFFIXES.some((s) => f.name.toLowerCase().endsWith(s)),
    );
    if (eligible.length === 0) {
      setUploadError(
        `No supported files selected. Accepted: ${ACCEPTED_SUFFIXES.join(", ")}`,
      );
      setUploadResult(null);
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    try {
      const result = await api.uploadFiles(eligible);
      setUploadResult(result);
      setRefreshTick((n) => n + 1);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  };

  const handleBrowseClick = () => {
    if (uploading) return;
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    // Reset so selecting the same file again re-fires the change event.
    e.target.value = "";
    void uploadFiles(files);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (uploading) return;
    const files = e.dataTransfer.files ? Array.from(e.dataTransfer.files) : [];
    void uploadFiles(files);
  };

  const handleDelete = async (runId: string) => {
    setOpenMenu(null);
    if (!window.confirm(`Delete run "${runId}"? This removes all documents, catalog rows, and traces for it.`)) {
      return;
    }
    setBusyId(runId);
    try {
      await api.deleteRun(runId);
      setRefreshTick((n) => n + 1);
    } catch (err) {
      window.alert(`Delete failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div ref={menuRootRef} className="flex flex-col gap-6">
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
      <div
        onClick={handleBrowseClick}
        onDragOver={(e) => {
          e.preventDefault();
          if (!uploading) setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleBrowseClick();
          }
        }}
        className={`w-full border-2 border-dashed rounded-xl p-12 flex flex-col items-center justify-center text-center transition-colors cursor-pointer ${
          dragActive
            ? "border-secondary bg-surface-container"
            : "border-outline-variant bg-surface-container-low hover:border-secondary hover:bg-surface-container"
        } ${uploading ? "opacity-60 cursor-progress" : ""}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_SUFFIXES.join(",")}
          className="hidden"
          onChange={handleFileInputChange}
        />
        <div className="bg-surface-container-highest p-4 rounded-full mb-4">
          <Icon
            name={uploading ? "hourglass_top" : "cloud_upload"}
            className="text-4xl text-on-surface-variant"
          />
        </div>
        <h3 className="text-headline-sm text-on-surface mb-2">
          {uploading ? "Uploading…" : "Drag & Drop Files"}
        </h3>
        <p className="text-body-md text-on-surface-variant mb-6 max-w-md">
          Supported formats: {ACCEPTED_SUFFIXES.join(", ")}. Max batch size:
          200 MB.
        </p>
        <button
          type="button"
          disabled={uploading}
          onClick={(e) => {
            e.stopPropagation();
            handleBrowseClick();
          }}
          className="border border-outline bg-surface-container-lowest px-6 py-2 rounded text-label-caps text-on-surface hover:bg-surface-container-highest transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? "Uploading…" : "Browse Files"}
        </button>
        {uploadError && (
          <p className="mt-4 text-label-caps text-error">{uploadError}</p>
        )}
        {uploadResult && (
          <div className="mt-4 text-label-caps text-secondary font-mono">
            Ingested {uploadResult.files_ingested}/{uploadResult.files_received}
            {uploadResult.files_failed > 0 &&
              ` · ${uploadResult.files_failed} failed`}
            {uploadResult.skipped.length > 0 &&
              ` · ${uploadResult.skipped.length} skipped`}
            <span className="text-on-surface-variant ml-2">
              run {uploadResult.run_id.slice(0, 8)}
            </span>
          </div>
        )}
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
                    className={`border-b border-outline-variant/30 row-data ${
                      busyId === u.id ? "opacity-50" : ""
                    }`}
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
                    <td className="py-3 px-4 text-right relative">
                      {copiedId === u.id && (
                        <span className="absolute right-12 top-1/2 -translate-y-1/2 text-label-sm text-secondary font-mono">
                          Copied
                        </span>
                      )}
                      <button
                        type="button"
                        aria-haspopup="menu"
                        aria-expanded={openMenu === u.id}
                        disabled={busyId === u.id}
                        onClick={() =>
                          setOpenMenu((cur) => (cur === u.id ? null : u.id))
                        }
                        className="text-on-surface-variant hover:text-primary transition-colors disabled:cursor-not-allowed"
                      >
                        <Icon name="more_horiz" className="text-[20px]" />
                      </button>
                      {openMenu === u.id && (
                        <div
                          role="menu"
                          className="absolute right-2 top-full mt-1 z-20 min-w-[180px] bg-surface-container-highest border border-outline-variant rounded-md shadow-lg py-1 text-left"
                        >
                          <button
                            type="button"
                            role="menuitem"
                            onClick={() => handleView(u.id)}
                            className="w-full px-3 py-2 text-body-md text-on-surface hover:bg-surface-container-high flex items-center gap-2"
                          >
                            <Icon name="open_in_new" className="text-[16px]" />
                            View in catalog
                          </button>
                          <button
                            type="button"
                            role="menuitem"
                            onClick={() => handleCopy(u.id)}
                            className="w-full px-3 py-2 text-body-md text-on-surface hover:bg-surface-container-high flex items-center gap-2"
                          >
                            <Icon name="content_copy" className="text-[16px]" />
                            Copy run ID
                          </button>
                          <button
                            type="button"
                            role="menuitem"
                            onClick={() => handleDelete(u.id)}
                            className="w-full px-3 py-2 text-body-md text-error hover:bg-error-container/40 flex items-center gap-2"
                          >
                            <Icon name="delete" className="text-[16px]" />
                            Delete
                          </button>
                        </div>
                      )}
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
