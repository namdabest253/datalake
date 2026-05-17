import { Icon } from "@/components/Icon";

type Props = {
  totalDocs?: string;
  throughput?: string;
};

export function TopBar({
  totalDocs = "Total: 1.2M",
  throughput = "1,240 Docs/sec",
}: Props) {
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
              Throughput
            </span>
            <span className="font-mono text-data-mono text-primary animate-flash">
              {throughput}
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
          <button className="p-2 rounded hover:bg-surface-container-high transition-colors active:opacity-80">
            <Icon name="sensors" />
          </button>
          <button className="p-2 rounded hover:bg-surface-container-high transition-colors active:opacity-80">
            <Icon name="memory" />
          </button>
          <button className="p-2 rounded hover:bg-surface-container-high transition-colors active:opacity-80">
            <Icon name="account_circle" />
          </button>
        </div>
      </div>
    </header>
  );
}
