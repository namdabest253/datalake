export function Footer({ offsetSidebar = false }: { offsetSidebar?: boolean }) {
  return (
    <footer
      className={`w-full bg-surface-container-low border-t border-outline-variant flex flex-col md:flex-row justify-between items-center px-margin-desktop py-6 gap-4 ${
        offsetSidebar ? "md:ml-[240px] md:w-[calc(100%-240px)]" : ""
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="text-label-caps font-bold">DATALAKE</span>
        <span className="text-body-md text-on-surface-variant/70">|</span>
        <span className="text-label-sm font-mono text-on-surface-variant">
          © 2026 Datalake Research Intelligence. Academic License.
        </span>
      </div>
      <div className="flex items-center gap-6">
        <a
          href="/PRD.md"
          target="_blank"
          rel="noreferrer"
          className="text-label-sm font-mono text-on-surface-variant hover:text-primary transition-colors"
        >
          PRD
        </a>
        <a
          href="/docs/00-overview.md"
          target="_blank"
          rel="noreferrer"
          className="text-label-sm font-mono text-on-surface-variant hover:text-primary transition-colors"
        >
          Design Docs
        </a>
        <a
          href="http://localhost:8000/api/health"
          target="_blank"
          rel="noreferrer"
          className="text-label-sm font-mono text-on-surface-variant hover:text-primary transition-colors"
        >
          API Health
        </a>
      </div>
    </footer>
  );
}
