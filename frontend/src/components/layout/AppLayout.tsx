import { Outlet } from "react-router-dom";
import { SideNav } from "./SideNav";
import { TopBar } from "./TopBar";
import { Footer } from "./Footer";

export function AppLayout() {
  return (
    <div className="min-h-screen flex bg-background text-on-surface">
      <SideNav />
      <div className="flex-1 md:ml-[240px] flex flex-col min-h-screen">
        <TopBar />
        <main className="flex-1 pt-20 px-margin-mobile md:px-margin-desktop pb-12 bg-background overflow-y-auto">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  );
}
