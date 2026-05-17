import { Icon } from "@/components/Icon";
import { EVAL_DIMENSIONS } from "@/data/mock";

export default function Eval() {
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
            <h3 className="text-headline-sm text-on-surface">
              Novel Transformer Architectures.pdf
            </h3>
          </div>
        </div>
        <div className="flex gap-3">
          <Chip>Bioinformatics</Chip>
          <Chip>24 Pages</Chip>
        </div>
      </div>

      {/* Side-by-side panels */}
      <div className="col-span-12 lg:col-span-6 flex flex-col gap-4">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg flex flex-col h-[500px] overflow-hidden shadow-sm relative">
          <div className="absolute top-0 w-full h-1 bg-outline-variant" />
          <div className="px-5 py-4 border-b border-outline-variant bg-surface-container/30 flex justify-between items-center">
            <div>
              <p className="text-label-caps text-outline">Baseline Model</p>
              <h4 className="text-headline-sm text-on-surface">
                GPT-4 Single Pass
              </h4>
            </div>
            <Icon name="speed" className="text-outline" />
          </div>
          <div className="p-5 overflow-y-auto flex-1 space-y-4">
            <div>
              <p className="text-label-caps text-outline mb-2">
                Extracted Summary
              </p>
              <p className="text-body-md text-on-surface-variant bg-surface-container-low p-3 rounded border border-outline-variant/30">
                The paper introduces a new transformer model aimed at improving
                processing efficiency for biological sequences. It suggests
                modifications to the attention mechanism to reduce computational
                overhead.
              </p>
            </div>
            <div>
              <p className="text-label-caps text-outline mb-2">
                Methodology Tags
              </p>
              <div className="flex gap-2 flex-wrap">
                <Tag>Attention Mechanism</Tag>
                <Tag>Efficiency</Tag>
              </div>
            </div>
            <div className="mt-4 p-3 bg-error-container/20 border border-error/20 rounded flex gap-3">
              <Icon name="warning" className="text-error text-sm mt-0.5" />
              <p className="text-label-sm font-mono text-on-surface-variant">
                Warning: Methodology specifics and dataset constraints are
                abstracted. Novelty claim lacks clear attribution to source
                sections.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="col-span-12 lg:col-span-6 flex flex-col gap-4">
        <div className="bg-surface-container-lowest border border-secondary/30 rounded-lg flex flex-col h-[500px] overflow-hidden shadow-float relative">
          <div className="absolute top-0 w-full h-1 bg-secondary-fixed" />
          <div className="px-5 py-4 border-b border-outline-variant bg-surface-container/30 flex justify-between items-center">
            <div>
              <p className="text-label-caps text-secondary">Inference Engine</p>
              <h4 className="text-headline-sm text-on-surface">
                Datalake Agent Loop
              </h4>
            </div>
            <Icon name="memory" className="text-secondary" />
          </div>
          <div className="p-5 overflow-y-auto flex-1 space-y-4">
            <div>
              <p className="text-label-caps text-secondary mb-2">
                Novelty Claim Extraction
              </p>
              <p className="text-body-md text-on-surface bg-secondary/5 p-3 rounded border border-secondary/20">
                Introduces 'Sparse-Bio-Attention', reducing algorithmic
                complexity from O(n²) to O(n log n) specifically for genomic
                sequences longer than 10,000 base pairs, maintaining 98%
                accuracy against full-attention baselines.
              </p>
              <p className="font-mono text-label-sm text-outline mt-1 ml-2">
                Source: Sec 3.2, Pg 8
              </p>
            </div>
            <div>
              <p className="text-label-caps text-secondary mb-2">
                Methodology Tags
              </p>
              <div className="flex gap-2 flex-wrap">
                <DataTag>Sparse-Bio-Attention</DataTag>
                <DataTag>O(n log n) Complexity</DataTag>
                <DataTag>Genomic Benchmarking</DataTag>
              </div>
            </div>
            <div>
              <p className="text-label-caps text-secondary mb-2">
                Claim Graph
              </p>
              <div className="h-20 bg-surface-container rounded border border-outline-variant/30 flex items-center justify-center gap-4 relative overflow-hidden px-4">
                <GraphNode>Model</GraphNode>
                <div className="w-8 h-px bg-secondary-fixed" />
                <GraphNode>Improves</GraphNode>
                <div className="w-8 h-px bg-secondary-fixed" />
                <GraphNode>Efficiency</GraphNode>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Verdict bar */}
      <div className="col-span-12 mt-2">
        <div className="bg-secondary text-on-secondary px-6 py-4 rounded-lg flex justify-between items-center shadow-float">
          <div className="flex items-center gap-4">
            <Icon name="verified" filled className="text-3xl" />
            <div>
              <h3 className="text-headline-md font-bold">
                Datalake (+68% Quality Delta)
              </h3>
              <p className="text-label-caps text-on-secondary/80">
                Higher accuracy and detail extraction across 100 benchmarked
                queries.
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
          Win Rates: Datalake vs Baseline
        </h4>
        <div className="space-y-6">
          {EVAL_DIMENSIONS.map((d) => (
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

function GraphNode({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-20 h-8 border border-secondary/50 rounded bg-secondary/10 flex items-center justify-center text-[10px] font-mono text-secondary">
      {children}
    </div>
  );
}
