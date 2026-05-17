import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "@/components/Icon";
import { GlassCard } from "@/components/GlassCard";
import { LoopTracker } from "@/components/LoopTracker";
import {
  api,
  type LoopMetrics,
  type TraceItem,
  type UnprocessedDoc,
  type UploadResult,
} from "@/api/client";
import { useApi } from "@/api/useApi";

const ACCEPTED_SUFFIXES = [".pdf", ".txt", ".md", ".json"];

// Material-ish palette for bar chart; cycles if there are more formats than colours.
const BAR_PALETTE = ["bg-secondary", "bg-primary", "bg-outline", "bg-error"];

type SortKey = "filename" | "ingested_at" | "run";

export default function Ingestion() {
  const [refreshTick, setRefreshTick] = useState(0);
  const [pollTick, setPollTick] = useState(0);
  const uploads = useApi(() => api.recentUploads(), [refreshTick, pollTick], {
    cacheKey: "ingestion:uploads",
  });
  const formats = useApi(() => api.formatDistribution(), [pollTick], {
    cacheKey: "ingestion:formats",
  });
  const traces = useApi(() => api.activeTraces(), [pollTick], {
    cacheKey: "ingestion:traces",
  });
  const rows = uploads.data ?? [];
  const formatBars = (formats.data ?? []).slice(0, 4);
  const loopRunning = traces.data?.loop_running ?? false;
  const loopTotalDocs = traces.data?.loop_total_docs ?? 0;
  const traceList = traces.data?.traces ?? [];
  const traceAvailable = traceList.length > 0;
  const loopMetrics = traces.data?.metrics ?? null;

  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [startNotice, setStartNotice] = useState<string | null>(null);
  const navigate = useNavigate();
  const menuRootRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Poll trace + recent uploads every 2s while a loop is running. Historical
  // traces persist in the UI after the loop ends, but they don't change once
  // the loop is idle, so polling can stop. The last in-flight poll captures
  // the post-completion state when loop_running flips to false.
  useEffect(() => {
    if (!loopRunning) return;
    const id = window.setInterval(() => setPollTick((n) => n + 1), 2000);
    return () => window.clearInterval(id);
  }, [loopRunning]);

  // Auto-dismiss the start notice ("nothing to do" etc.) after a few seconds.
  useEffect(() => {
    if (!startNotice) return;
    const id = window.setTimeout(() => setStartNotice(null), 4000);
    return () => window.clearTimeout(id);
  }, [startNotice]);

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
        <div className="flex flex-col items-end gap-2">
          <button
            type="button"
            onClick={() => {
              setStartError(null);
              setStartNotice(null);
              setPickerOpen(true);
            }}
            disabled={loopRunning}
            className={`bg-secondary text-on-secondary px-6 py-3 rounded text-label-caps shadow-sm transition-opacity flex items-center gap-2 ${
              loopRunning ? "opacity-60 cursor-not-allowed" : "hover:opacity-90"
            }`}
          >
            <Icon name={loopRunning ? "hourglass_top" : "hub"} />
            {loopRunning ? "Loop running…" : "Start Multi-Pass Agent Loop"}
          </button>
          {startError && (
            <span className="text-label-caps text-error">{startError}</span>
          )}
          {startNotice && (
            <span className="text-label-caps text-secondary">{startNotice}</span>
          )}
        </div>
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

      {/* Inline agent-loop progress — shows when a loop is running or has just
          finished, so the user gets live visual feedback without leaving the page.
          Renders up to 4 concurrent trace cards (wafer concurrency cap), but only
          as many as docs the user actually selected. */}
      {(loopRunning || traceAvailable) && (
        <GlassCard className="p-6 mt-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-headline-sm text-on-surface">
                Agent Loop Progress
              </h3>
              <p className="text-label-caps text-on-surface-variant mt-1">
                {loopRunning
                  ? `Processing ${loopTotalDocs} document${loopTotalDocs === 1 ? "" : "s"}` +
                    (traceList.length > 0
                      ? ` · ${traceList.length} active`
                      : "") +
                    "…"
                  : "Loop idle — last trace shown below."}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/app/dashboard")}
              className="text-label-caps text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1"
            >
              Open Dashboard
              <Icon name="open_in_new" className="text-[16px]" />
            </button>
          </div>
          <LoopMetricsStrip metrics={loopMetrics} running={loopRunning} />
          <TraceGrid
            traces={traceList}
            loading={traces.loading}
            error={traces.error}
          />
        </GlassCard>
      )}

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

      {pickerOpen && (
        <StartLoopModal
          onClose={() => setPickerOpen(false)}
          onStarted={(msg) => {
            if (msg) setStartNotice(msg);
            setPollTick((n) => n + 1);
            setRefreshTick((n) => n + 1);
          }}
          onError={(msg) => setStartError(msg)}
        />
      )}
    </div>
  );
}

function StartLoopModal({
  onClose,
  onStarted,
  onError,
}: {
  onClose: () => void;
  onStarted: (notice: string | null) => void;
  onError: (msg: string) => void;
}) {
  const docs = useApi(() => api.unprocessedDocuments(), [], {
    cacheKey: "ingestion:unprocessedDocs",
  });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [lastClickedId, setLastClickedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("run");
  const [starting, setStarting] = useState(false);
  const [initialised, setInitialised] = useState(false);

  // Pre-select all docs in the newest run, once the API responds.
  useEffect(() => {
    if (initialised || !docs.data) return;
    const newest = docs.data.newest_run_id;
    if (newest) {
      setSelected(
        new Set(
          docs.data.documents
            .filter((d) => d.run_id === newest)
            .map((d) => d.id),
        ),
      );
    }
    setInitialised(true);
  }, [docs.data, initialised]);

  const visible = useMemo<UnprocessedDoc[]>(() => {
    const all = docs.data?.documents ?? [];
    const q = search.trim().toLowerCase();
    const filtered = q
      ? all.filter((d) => d.filename.toLowerCase().includes(q))
      : all;
    const sorted = [...filtered];
    sorted.sort((a, b) => {
      if (sortKey === "filename") return a.filename.localeCompare(b.filename);
      if (sortKey === "ingested_at") return a.ingested_at - b.ingested_at;
      // "run": newest run first, then ingest order within run.
      if (a.run_id !== b.run_id) return b.run_started_at - a.run_started_at;
      return a.ingested_at - b.ingested_at;
    });
    return sorted;
  }, [docs.data, search, sortKey]);

  const visibleIds = useMemo(() => visible.map((d) => d.id), [visible]);

  const onRowToggle = (id: string, shift: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (shift && lastClickedId && lastClickedId !== id) {
        const a = visibleIds.indexOf(lastClickedId);
        const b = visibleIds.indexOf(id);
        if (a >= 0 && b >= 0) {
          const [lo, hi] = a < b ? [a, b] : [b, a];
          const targetState = !prev.has(id);
          for (let i = lo; i <= hi; i++) {
            if (targetState) next.add(visibleIds[i]);
            else next.delete(visibleIds[i]);
          }
          return next;
        }
      }
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setLastClickedId(id);
  };

  const selectAllVisible = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const id of visibleIds) next.add(id);
      return next;
    });
  };
  const clearSelection = () => setSelected(new Set());

  const handleStart = async () => {
    const ids = [...selected];
    if (ids.length === 0) return;
    setStarting(true);
    try {
      const res = await api.startLoop(ids);
      if (res.status === "nothing_to_do") {
        onStarted(res.message);
      } else {
        onStarted(`Loop started on ${res.doc_count} document${res.doc_count === 1 ? "" : "s"}.`);
      }
      onClose();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  };

  // Group visible docs by run for a subtle visual divider in the list.
  const groupedRuns = useMemo(() => {
    const seen = new Map<string, { run_id: string; started_at: number }>();
    for (const d of visible) {
      if (!seen.has(d.run_id))
        seen.set(d.run_id, { run_id: d.run_id, started_at: d.run_started_at });
    }
    return seen;
  }, [visible]);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-scrim/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-surface-container-lowest border border-outline-variant rounded-xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col shadow-float"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant">
          <div className="min-w-0">
            <p className="text-label-caps text-on-surface-variant">
              Start Multi-Pass Agent Loop
            </p>
            <h2 className="text-headline-sm text-on-surface truncate">
              Select documents to process
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

        <div className="px-6 py-3 border-b border-outline-variant flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[180px] relative">
            <Icon
              name="search"
              className="absolute left-2 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search filenames…"
              className="w-full pl-8 pr-3 py-1.5 rounded border border-outline-variant bg-surface-container-lowest text-body-md text-on-surface focus:outline-none focus:border-secondary"
            />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-label-caps text-on-surface-variant mr-1">
              Sort:
            </span>
            <SortButton current={sortKey} value="run" onClick={setSortKey}>
              Run
            </SortButton>
            <SortButton current={sortKey} value="filename" onClick={setSortKey}>
              Name
            </SortButton>
            <SortButton current={sortKey} value="ingested_at" onClick={setSortKey}>
              Ingested
            </SortButton>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {docs.loading && (
            <p className="px-6 py-6 text-on-surface-variant text-label-caps">
              Loading queued documents…
            </p>
          )}
          {docs.error && (
            <p className="px-6 py-6 text-error text-label-caps">
              API error: {docs.error}. Is `datalake api` running?
            </p>
          )}
          {!docs.loading && !docs.error && visible.length === 0 && (
            <p className="px-6 py-6 text-on-surface-variant text-label-caps">
              {docs.data && docs.data.documents.length === 0
                ? "No queued documents. Upload some files first."
                : "No documents match the current filter."}
            </p>
          )}
          {visible.length > 0 && (
            <ul className="divide-y divide-outline-variant/40">
              {visible.map((doc, idx) => {
                const prev = idx > 0 ? visible[idx - 1] : null;
                const isNewGroup =
                  sortKey === "run" && (!prev || prev.run_id !== doc.run_id);
                const checked = selected.has(doc.id);
                return (
                  <li key={doc.id}>
                    {isNewGroup && (
                      <div className="px-6 py-2 bg-surface-container-low text-label-caps text-on-surface-variant flex items-center justify-between">
                        <span>
                          Run {doc.run_id.slice(0, 8)} ·{" "}
                          {groupedRuns.get(doc.run_id) &&
                            new Date(
                              groupedRuns.get(doc.run_id)!.started_at * 1000,
                            ).toLocaleString()}
                        </span>
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={(e) => onRowToggle(doc.id, e.shiftKey)}
                      className={`w-full px-6 py-2 flex items-center gap-3 text-left hover:bg-surface-container-low transition-colors ${
                        checked ? "bg-secondary/10" : ""
                      }`}
                    >
                      <span
                        className={`w-4 h-4 shrink-0 rounded border flex items-center justify-center ${
                          checked
                            ? "bg-secondary border-secondary"
                            : "border-outline"
                        }`}
                      >
                        {checked && (
                          <Icon name="check" className="text-[12px] text-on-secondary" />
                        )}
                      </span>
                      <Icon
                        name="description"
                        className="text-on-surface-variant text-[18px] shrink-0"
                      />
                      <span className="font-mono text-data-mono text-on-surface truncate flex-1">
                        {doc.filename}
                      </span>
                      <span className="text-label-sm text-on-surface-variant font-mono shrink-0">
                        {doc.content_type ?? "—"}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="px-6 py-4 border-t border-outline-variant flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={selectAllVisible}
              disabled={visible.length === 0}
              className="text-label-caps text-on-surface-variant hover:text-primary transition-colors disabled:opacity-40"
            >
              Select all visible
            </button>
            <span className="text-outline">·</span>
            <button
              type="button"
              onClick={clearSelection}
              disabled={selected.size === 0}
              className="text-label-caps text-on-surface-variant hover:text-primary transition-colors disabled:opacity-40"
            >
              Clear
            </button>
            <span className="text-label-caps text-on-surface-variant ml-3">
              {selected.size} selected · tip: shift-click to range-select
            </span>
          </div>
          <button
            type="button"
            onClick={handleStart}
            disabled={starting || selected.size === 0}
            className="bg-secondary text-on-secondary px-5 py-2 rounded text-label-caps flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
          >
            <Icon name={starting ? "hourglass_top" : "play_arrow"} />
            {starting ? "Starting…" : "Start Loop"}
          </button>
        </div>
      </div>
    </div>
  );
}

function LoopMetricsStrip({
  metrics,
  running,
}: {
  metrics: LoopMetrics | null;
  running: boolean;
}) {
  // Strip is only worth showing once at least one real call has been logged —
  // empty zeros pre-flight would just be noise above the trace cards.
  if (!metrics || !metrics.available) return null;

  const tiles: Array<{
    label: string;
    value: string;
    sub?: string;
    accent?: boolean;
  }> = [
    {
      label: "Latency p50",
      value: fmtLatency(metrics.latency_p50_ms),
      sub: "per Wafer call",
    },
    {
      label: "Latency p95",
      value: fmtLatency(metrics.latency_p95_ms),
      sub: "tail",
    },
    {
      label: "TTFT ~",
      value: fmtLatency(metrics.ttft_ms),
      sub: "regression est.",
    },
    {
      label: "Throughput",
      value:
        metrics.tokens_per_sec !== null
          ? `${metrics.tokens_per_sec.toFixed(0)} tok/s`
          : "—",
      sub: "output, median",
      accent: true,
    },
  ];

  const savings = metrics.savings_x;
  const savingsLabel =
    savings !== null && savings >= 1
      ? `~${savings.toFixed(savings >= 10 ? 0 : 1)}× cheaper than GPT-4`
      : null;

  return (
    <div className="mb-5 flex flex-col gap-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {tiles.map((t) => (
          <div
            key={t.label}
            className={`rounded-lg border px-3 py-2 ${
              t.accent
                ? "border-secondary/40 bg-secondary/10"
                : "border-outline-variant/40 bg-surface-container-low"
            }`}
          >
            <div className="text-label-caps text-on-surface-variant">
              {t.label}
            </div>
            <div
              className={`font-mono text-headline-sm leading-tight mt-0.5 ${
                t.accent ? "text-secondary" : "text-on-surface"
              }`}
            >
              {t.value}
            </div>
            {t.sub && (
              <div className="text-label-sm font-mono text-outline mt-0.5">
                {t.sub}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-outline-variant/40 bg-surface-container-low px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="flex items-baseline gap-2">
          <span className="text-label-caps text-on-surface-variant">
            Wafer spend
          </span>
          <span className="font-mono text-headline-sm text-primary">
            {fmtUsd(metrics.wafer_usd)}
          </span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-label-caps text-on-surface-variant">
            GPT-4 equiv.
          </span>
          <span className="font-mono text-body-md text-outline line-through">
            {fmtUsd(metrics.gpt4_usd)}
          </span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-label-caps text-on-surface-variant">Calls</span>
          <span className="font-mono text-body-md text-on-surface">
            {metrics.calls.toLocaleString()}
          </span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-label-caps text-on-surface-variant">Tokens</span>
          <span className="font-mono text-body-md text-on-surface">
            {fmtTokens(metrics.tokens_in)} in / {fmtTokens(metrics.tokens_out)} out
          </span>
        </div>
        {savingsLabel && (
          <div className="ml-auto px-3 py-1 rounded-full bg-secondary text-on-secondary text-label-caps font-bold tracking-wider flex items-center gap-1">
            <Icon name="trending_down" className="text-[16px]" />
            {savingsLabel}
          </div>
        )}
        {running && (
          <div className="flex items-center gap-1 text-label-sm text-secondary font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-flash" />
            live
          </div>
        )}
      </div>
    </div>
  );
}

function fmtLatency(ms: number | null): string {
  if (ms === null) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`;
  return `${ms} ms`;
}

function fmtUsd(n: number): string {
  if (n === 0) return "$0";
  if (n >= 1) return `$${n.toFixed(2)}`;
  if (n >= 0.01) return `$${n.toFixed(4)}`;
  return `$${n.toFixed(6)}`;
}

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toLocaleString();
}

function TraceGrid({
  traces,
  loading,
  error,
}: {
  traces: TraceItem[];
  loading: boolean;
  error: string | null;
}) {
  if (traces.length === 0) {
    return (
      <div className="min-h-[360px]">
        <LoopTracker trace={null} loading={loading} error={error} />
      </div>
    );
  }
  // Up to four cards side-by-side on wide screens; stack on smaller breakpoints
  // so a single-doc run isn't surrounded by empty grid cells.
  const cols =
    traces.length === 1
      ? "grid-cols-1"
      : traces.length === 2
        ? "grid-cols-1 md:grid-cols-2"
        : traces.length === 3
          ? "grid-cols-1 md:grid-cols-2 xl:grid-cols-3"
          : "grid-cols-1 md:grid-cols-2 xl:grid-cols-4";
  return (
    <div className={`grid ${cols} gap-4`}>
      {traces.map((t) => (
        <div
          key={t.doc_id}
          className="min-h-[360px] bg-surface-container-low rounded-lg border border-outline-variant/40 p-4"
        >
          <LoopTracker
            trace={{
              available: true,
              doc_id: t.doc_id,
              filename: t.filename,
              passes: t.passes,
              loop_running: false,
              loop_run_id: null,
              loop_total_docs: 0,
            }}
            loading={false}
            error={null}
          />
        </div>
      ))}
    </div>
  );
}

function SortButton({
  current,
  value,
  onClick,
  children,
}: {
  current: SortKey;
  value: SortKey;
  onClick: (v: SortKey) => void;
  children: React.ReactNode;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      onClick={() => onClick(value)}
      className={`px-2 py-1 rounded text-label-caps transition-colors ${
        active
          ? "bg-secondary/15 text-secondary"
          : "text-on-surface-variant hover:bg-surface-container-high"
      }`}
    >
      {children}
    </button>
  );
}
