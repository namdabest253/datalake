import { Icon } from "@/components/Icon";
import { GlassCard } from "@/components/GlassCard";
import { STREAM_ITEMS } from "@/data/mock";

const STATUS_STYLES: Record<
  string,
  { dot: string; text: string }
> = {
  Ready: { dot: "bg-secondary animate-flash", text: "text-secondary" },
  Extracting: { dot: "bg-secondary animate-flash", text: "text-secondary" },
  Failed: { dot: "bg-error", text: "text-error" },
  Queued: { dot: "bg-outline", text: "text-outline" },
};

export default function Dashboard() {
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
            {STREAM_ITEMS.map((item) => {
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
            Active Trace: arXiv:2405.0123.pdf
          </div>
          <div className="flex-1 relative flex flex-col justify-between pl-8">
            <div className="absolute left-[11px] top-4 bottom-4 w-px bg-outline-variant z-0" />
            <LoopStep
              done
              label="Read & Extract"
              sub="Parsed 14 pages, 2 tables"
            />
            <LoopStep done label="Propose Hypotheses">
              <div className="flex gap-2 mt-2">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-8 h-8 rounded border border-outline flex items-center justify-center bg-surface text-secondary"
                  >
                    <Icon name="psychology" className="text-[16px]" />
                  </div>
                ))}
              </div>
            </LoopStep>
            <LoopStep active label="Multi-Agent Critique">
              <div className="flex gap-2 mt-2">
                <div className="px-2 py-1 rounded bg-error-container text-on-error-container text-label-sm flex items-center gap-1">
                  <Icon name="close" className="text-[12px]" /> Reject 1
                </div>
                <div className="px-2 py-1 rounded bg-secondary-container text-on-secondary-container text-label-sm flex items-center gap-1">
                  <Icon name="check" className="text-[12px]" /> Accept 2
                </div>
              </div>
            </LoopStep>
            <LoopStep label="Refine Syntheses" muted />
            <LoopStep label="Enrich Payload" muted />
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
              <div className="text-headline-lg text-primary">$24.12</div>
              <div className="text-label-sm font-mono text-secondary mt-1">
                Wafer Local Inference
              </div>
            </div>
            <div className="text-right">
              <div className="text-headline-sm text-outline">$1,420.50</div>
              <div className="text-label-sm font-mono text-outline mt-1">
                GPT-4 Baseline Equivalent
              </div>
            </div>
          </div>
          <div className="w-full h-4 bg-surface-container-high rounded-full overflow-hidden flex relative">
            <div className="bg-outline-variant h-full opacity-30 absolute inset-0 w-full" />
            <div
              className="bg-secondary h-full relative z-10"
              style={{ width: "1.7%" }}
            />
          </div>
          <div className="text-right text-label-sm font-mono text-secondary mt-2 font-bold tracking-widest">
            ~58× SAVINGS
          </div>
        </GlassCard>
      </div>

      <div className="lg:col-span-4 mt-4 grid grid-cols-2 gap-4">
        <QualityDial pct={94} label="Inter-Agent\nAgreement" />
        <QualityDial pct={88} label="Overall\nConfidence" />
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
