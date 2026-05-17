import { Link } from "react-router-dom";
import { Icon } from "@/components/Icon";

export default function Landing() {
  return (
    <>
      {/* Hero */}
      <section className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop grid grid-cols-1 lg:grid-cols-12 gap-gutter items-center min-h-[640px] py-8">
        <div className="lg:col-span-6 flex flex-col gap-6 z-10">
          <div className="flex items-center gap-2 text-secondary font-mono text-data-mono">
            <Icon name="memory" className="text-[16px]" />
            <span>System Online // Inference Ready</span>
          </div>
          <h1 className="text-[48px] leading-[56px] font-bold text-on-surface tracking-tighter">
            Datalake: Make University Data Labelable.
          </h1>
          <p className="text-body-lg text-on-surface-variant max-w-xl">
            The agentic prep system for institutional research. Catalog
            compliance and label training-grade metadata in a single high-speed
            inference pass.
          </p>
          <div className="flex items-center gap-4 mt-4">
            <Link
              to="/app/dashboard"
              className="bg-primary text-on-primary text-label-caps px-6 py-3 rounded flex items-center gap-2 hover:bg-on-surface transition-colors"
            >
              Run Demo
              <Icon name="play_arrow" className="text-[18px]" />
            </Link>
            <a
              href="https://github.com/"
              className="border border-outline text-on-surface text-label-caps px-6 py-3 rounded flex items-center gap-2 hover:bg-surface-container transition-colors"
            >
              Read PRD
              <Icon name="description" className="text-[18px]" />
            </a>
          </div>
        </div>

        <div className="lg:col-span-6 relative h-[400px] lg:h-[560px] bg-primary-container rounded-xl border border-outline-variant overflow-hidden shadow-float mt-8 lg:mt-0">
          <video
            className="absolute inset-0 w-full h-full object-cover"
            src="/landing-bg-animation.mp4"
            autoPlay
            loop
            muted
            playsInline
            preload="auto"
            aria-hidden
          />
          <div className="absolute bottom-6 right-6 left-6 md:left-auto md:w-80 bg-surface-container-lowest/90 backdrop-blur-glass border border-outline-variant p-4 rounded-lg shadow-float">
            <div className="flex justify-between items-center mb-2">
              <span className="text-label-caps text-on-surface-variant">
                Live Inference Pass
              </span>
              <Icon
                name="sensors"
                filled
                className="text-secondary animate-flash"
              />
            </div>
            <div className="space-y-2 font-mono text-data-mono">
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Docs Processed</span>
                <span className="text-on-surface">1,245,890</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Speed</span>
                <span className="text-secondary">4,200/sec</span>
              </div>
              <div className="w-full bg-surface-container-high h-1.5 rounded-full mt-2 overflow-hidden">
                <div className="bg-secondary h-full rounded-full w-[85%]" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trusted by */}
      <section className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-16 border-y border-outline-variant/30 mt-12 bg-surface-container-low/50">
        <p className="text-center text-label-caps text-on-surface-variant mb-8 tracking-widest">
          Architected For
        </p>
        <div className="flex flex-wrap justify-center items-center gap-12 md:gap-24 opacity-60 grayscale">
          <div className="text-headline-sm font-bold">University CDOs</div>
          <div className="text-headline-sm font-bold">OpenAI Labs</div>
          <div className="text-headline-sm font-bold">Anthropic</div>
          <div className="text-headline-sm font-bold">Compliance Officers</div>
        </div>
      </section>

      {/* Economics */}
      <section className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-24">
        <div className="text-center mb-16">
          <h2 className="text-headline-lg text-on-surface mb-4">
            The Economics of Inference
          </h2>
          <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            Why human labeling and standard LLMs fail at institutional scale,
            and how Datalake on Wafer unlocks the market.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <EconCard
            iconName="person_off"
            iconClass="text-error"
            title="Human Labeling"
            cost="$30.00"
            unit="/ paper"
            body="Prohibitively expensive for massive datasets. Slow turnaround times and variable quality."
            statusLabel="Status: Fails at Scale"
            statusClass="text-error"
          />
          <EconCard
            iconName="smart_toy"
            iconClass="text-on-surface-variant"
            title="Standard GPT-4"
            cost="$1.00"
            unit="/ paper"
            body="Better speed, but cost remains a bottleneck for multi-million document archives. Generalist context."
            statusLabel="Status: Economically Infeasible"
            statusClass="text-on-surface-variant"
          />
          <EconCard
            iconName="speed"
            iconFilled
            iconClass="text-secondary"
            title="Datalake on Wafer"
            cost="¢0.02"
            unit="/ paper"
            body="Customized inference passes. Specialized agent loops optimize for extreme cost-efficiency and academic precision."
            statusLabel="Status: Inference Ready"
            statusClass="text-secondary"
            highlight
          />
        </div>

        <div className="mt-16 bg-surface-container-lowest border border-outline-variant rounded-xl p-8">
          <h4 className="text-label-caps text-on-surface-variant mb-6">
            Cost vs. Quality Trajectory
          </h4>
          <div className="space-y-6">
            <ChartRow label="Human" costPct={90} qualityPct={20} />
            <ChartRow label="GPT-4" costPct={40} qualityPct={50} />
            <ChartRow label="Datalake" costPct={5} qualityPct={85} highlight />
          </div>
          <div className="flex justify-center gap-8 mt-6 pt-4 border-t border-outline-variant/30">
            <Legend color="bg-outline" label="Cost Factor" />
            <Legend color="bg-secondary" label="Quality Factor" />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <Feature
            iconName="fact_check"
            title="Catalog Inference"
            body="Automatically structure unstructured university archives. Map entities, relationships, and compliance risks across millions of PDFs in hours."
          />
          <Feature
            iconName="label"
            title="Rich Labeling"
            body="Generate training-grade metadata. Assign granular tags, methodology, evidence quality, and citation graphs to every document."
          />
          <Feature
            iconName="all_inclusive"
            title="Multi-Pass Agent Loops"
            body="Propose → Critique → Refine → Vote → Enrich. Agents critique each other's work to ensure low hallucination in the final dataset."
          />
        </div>
      </section>

      <footer className="w-full bg-surface-container-low border-t border-outline-variant flex flex-col md:flex-row justify-between items-center px-margin-desktop py-6 gap-4">
        <div className="text-label-caps font-bold">DATALAKE</div>
        <div className="flex gap-6">
          <a
            href="#"
            className="text-on-surface-variant hover:text-primary text-label-sm font-mono"
          >
            Ethics Policy
          </a>
          <a
            href="#"
            className="text-on-surface-variant hover:text-primary text-label-sm font-mono"
          >
            University Partners
          </a>
          <a
            href="#"
            className="text-on-surface-variant hover:text-primary text-label-sm font-mono"
          >
            API Docs
          </a>
        </div>
        <div className="text-body-md text-on-surface-variant">
          © 2026 Datalake Research Intelligence. Academic License.
        </div>
      </footer>
    </>
  );
}

type EconCardProps = {
  iconName: string;
  iconFilled?: boolean;
  iconClass: string;
  title: string;
  cost: string;
  unit: string;
  body: string;
  statusLabel: string;
  statusClass: string;
  highlight?: boolean;
};

function EconCard({
  iconName,
  iconFilled,
  iconClass,
  title,
  cost,
  unit,
  body,
  statusLabel,
  statusClass,
  highlight,
}: EconCardProps) {
  return (
    <div
      className={`bg-surface-container-lowest p-6 rounded-xl flex flex-col relative ${
        highlight
          ? "border-2 border-secondary shadow-glass-sm"
          : "border border-outline-variant"
      }`}
    >
      {highlight && (
        <div className="absolute -top-3 right-6 bg-secondary text-on-secondary text-label-caps px-3 py-1 rounded-full">
          Market Unlocked
        </div>
      )}
      <div className={`mb-4 ${iconClass}`}>
        <Icon name={iconName} filled={iconFilled} className="text-[32px]" />
      </div>
      <h3 className="text-headline-md mb-2">{title}</h3>
      <div
        className={`font-mono text-[24px] mb-4 ${
          highlight ? "text-secondary" : "text-on-surface"
        }`}
      >
        {cost}
        <span className="text-[14px] text-on-surface-variant"> {unit}</span>
      </div>
      <p className="text-body-md text-on-surface-variant flex-grow">{body}</p>
      <div
        className={`mt-6 pt-4 border-t border-outline-variant/50 font-mono text-label-sm ${statusClass}`}
      >
        {statusLabel}
      </div>
    </div>
  );
}

function ChartRow({
  label,
  costPct,
  qualityPct,
  highlight,
}: {
  label: string;
  costPct: number;
  qualityPct: number;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center gap-4">
      <div
        className={`w-32 font-mono text-label-sm text-right ${
          highlight ? "font-bold text-secondary" : ""
        }`}
      >
        {label}
      </div>
      <div className="flex-grow flex h-4">
        <div
          className="bg-outline h-full rounded-l"
          style={{ width: `${costPct}%` }}
        />
        <div
          className={`bg-secondary h-full rounded-r ${
            highlight ? "shadow-[0_0_10px_rgba(0,107,95,0.4)]" : ""
          }`}
          style={{ width: `${qualityPct}%` }}
        />
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 ${color} rounded-sm`} />
      <span className="text-label-sm font-mono text-on-surface-variant">
        {label}
      </span>
    </div>
  );
}

function Feature({
  iconName,
  title,
  body,
}: {
  iconName: string;
  title: string;
  body: string;
}) {
  return (
    <div className="flex flex-col gap-3">
      <Icon
        name={iconName}
        filled
        className="text-[28px] text-primary"
      />
      <h3 className="text-headline-sm text-on-surface">{title}</h3>
      <p className="text-body-md text-on-surface-variant">{body}</p>
    </div>
  );
}
