import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";

import "./index.css";
import { AppLayout } from "@/components/layout/AppLayout";
import { MarketingLayout } from "@/components/layout/MarketingLayout";
import Landing from "@/pages/Landing";
import Dashboard from "@/pages/Dashboard";
import Ingestion from "@/pages/Ingestion";
import Catalog from "@/pages/Catalog";
import Eval from "@/pages/Eval";
import ExportPage from "@/pages/Export";

const router = createBrowserRouter([
  {
    element: <MarketingLayout />,
    children: [{ path: "/", element: <Landing /> }],
  },
  {
    path: "/app",
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "dashboard", element: <Dashboard /> },
      { path: "ingestion", element: <Ingestion /> },
      { path: "catalog", element: <Catalog /> },
      { path: "eval", element: <Eval /> },
      { path: "export", element: <ExportPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
