import { Link, Outlet } from "react-router-dom";

export function MarketingLayout() {
  return (
    <div className="min-h-screen bg-background text-on-surface">
      <header className="w-full h-16 flex justify-between items-center px-margin-mobile md:px-margin-desktop bg-surface/80 backdrop-blur-glass border-b border-outline-variant shadow-sm fixed top-0 z-50">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="text-headline-sm font-bold tracking-tighter text-on-surface"
          >
            DATALAKE
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/app/dashboard"
            className="text-label-caps text-on-surface-variant hover:text-on-surface px-3 py-2 rounded transition-colors"
          >
            Open App
          </Link>
          <Link
            to="/app/dashboard"
            className="bg-primary text-on-primary text-label-caps px-4 py-2 rounded"
          >
            Run Demo
          </Link>
        </div>
      </header>
      <main className="pt-16">
        <Outlet />
      </main>
    </div>
  );
}
