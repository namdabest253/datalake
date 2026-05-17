import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { SideNav } from "./SideNav";
import { TopBar } from "./TopBar";
import { Footer } from "./Footer";

export function AppLayout() {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [location.pathname]);
  return (
    <div className="min-h-screen flex bg-background text-on-surface">
      <SideNav />
      <div className="flex-1 md:ml-[240px] flex flex-col min-h-screen">
        <TopBar />
        <main className="flex-1 pt-20 px-margin-mobile md:px-margin-desktop pb-12 bg-background overflow-y-auto">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.32, ease: "easeInOut" }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
        <Footer />
      </div>
    </div>
  );
}
