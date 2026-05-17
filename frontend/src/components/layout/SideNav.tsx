import { Link, NavLink } from "react-router-dom";
import { Icon } from "@/components/Icon";

type NavItem = { to: string; label: string; icon: string };

const PRIMARY: NavItem[] = [
  { to: "/app/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/app/ingestion", label: "Ingestion Hub", icon: "upload_file" },
  { to: "/app/catalog", label: "Catalog & Compliance", icon: "fact_check" },
  { to: "/app/eval", label: "Quality Evaluation", icon: "analytics" },
  { to: "/app/export", label: "Export", icon: "ios_share" },
];

const linkBase =
  "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-150 text-label-caps";

const linkInactive =
  "text-on-primary-container/70 font-medium hover:text-on-primary-container hover:bg-on-primary-container/10";

const linkActive =
  "bg-secondary-container/20 text-secondary-fixed-dim font-bold border-r-4 border-secondary-fixed-dim translate-x-1";

export function SideNav() {
  return (
    <nav className="hidden md:flex fixed left-0 top-0 h-full w-[240px] z-50 flex-col py-margin-desktop gap-unit bg-primary-container text-on-primary-container border-r border-outline-variant">
      <div className="px-6 mb-8 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary-fixed flex items-center justify-center text-on-primary-fixed shrink-0">
          <Icon name="science" filled />
        </div>
        <div className="min-w-0">
          <h1 className="text-headline-md font-bold tracking-tight text-on-primary-container">
            DATALAKE
          </h1>
          <p className="text-label-caps text-on-primary-container/70">
            AI Inference Engine
          </p>
        </div>
      </div>

      <div className="flex-1 px-4 space-y-1 overflow-y-auto">
        {PRIMARY.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `${linkBase} ${isActive ? linkActive : linkInactive}`
            }
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="px-6 mb-6">
        <Link
          to="/app/ingestion"
          className="w-full bg-secondary text-on-secondary py-3 rounded text-label-caps flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
        >
          <Icon name="play_arrow" filled />
          Run New Agent
        </Link>
      </div>
    </nav>
  );
}
