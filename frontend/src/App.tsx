import React from "react";
import { Authenticated, Refine } from "@refinedev/core";
import { RefineKbarProvider } from "@refinedev/kbar";
import routerProvider, { NavigateToResource } from "@refinedev/react-router";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router";
import { ConfigProvider } from "antd";
import ruRU from "antd/locale/ru_RU";

import { dataProvider } from "./dataProvider";
import { authProvider } from "./authProvider";
import { showroomTheme } from "./theme";
import { AppShell } from "./layout/AppShell";
import { Login } from "./pages/Login";
import { UsersList } from "./pages/admin/UsersList";
import { UserCreate } from "./pages/admin/UserCreate";
import { UserEdit } from "./pages/admin/UserEdit";
import { AuditPage } from "./pages/admin/AuditPage";
import { BackupsPage } from "./pages/admin/BackupsPage";
import { HistoryPage } from "./pages/admin/HistoryPage";
import { CatalogPage, LocationsPage, SuppliersPage } from "./pages/admin/DirectoryPages";
import { ArchivePage, SupplyList } from "./pages/client/SupplyList";
import { SupplyCreate } from "./pages/client/SupplyCreate";
import { SupplyShow } from "./pages/client/SupplyShow";
import { NotificationsPage } from "./pages/client/NotificationsPage";
import { ReportsPage } from "./pages/client/ReportsPage";
import { QueuePage } from "./pages/validator/QueuePage";
import { HelpPage } from "./pages/HelpPage";

import "@refinedev/antd/dist/reset.css";
import "./index.css";

const adminResources = [
  { name: "users", list: "/users", create: "/users/create", edit: "/users/edit/:id", meta: { label: "Люди" } },
  { name: "suppliers", list: "/suppliers", meta: { label: "Поставщики" } },
  { name: "locations", list: "/locations", meta: { label: "Места" } },
  { name: "catalog", list: "/catalog", meta: { label: "Номенклатура" } },
  { name: "audit", list: "/audit", meta: { label: "Журнал" } },
  { name: "history", list: "/history", meta: { label: "История" } },
];

const clientResources = [
  { name: "supplies", list: "/supplies", create: "/supplies/create", show: "/supplies/:id", meta: { label: "Поставки" } },
  { name: "notifications", list: "/notifications", meta: { label: "Уведомления" } },
  { name: "reports", list: "/reports", meta: { label: "Отчёты" } },
];

const validatorResources = [
  { name: "queue", list: "/queue", meta: { label: "Очередь" } },
  { name: "notifications", list: "/notifications", meta: { label: "Уведомления" } },
];

function resourcesByRole(role: string | null) {
  if (role === "admin") return adminResources;
  if (role === "validator") return validatorResources;
  return clientResources;
}

const HOME_BY_ROLE: Record<string, string> = {
  admin: "/users",
  client: "/supplies",
  validator: "/queue",
};

const ALLOWED_BY_ROLE: Record<string, string[]> = {
  admin: ["/users", "/suppliers", "/locations", "/catalog", "/audit", "/history", "/backups", "/help"],
  client: ["/supplies", "/archive", "/notifications", "/reports", "/help"],
  validator: ["/queue", "/notifications", "/help"],
};

function pathAllowed(pathname: string, prefixes: string[]) {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function RoleGate({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const role = localStorage.getItem("role") || "client";
  const allowed = ALLOWED_BY_ROLE[role] ?? ALLOWED_BY_ROLE.client;
  if (!pathAllowed(location.pathname, allowed)) {
    return <Navigate to={HOME_BY_ROLE[role] ?? "/supplies"} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  const [role, setRole] = React.useState<string | null>(() => localStorage.getItem("role"));
  React.useEffect(() => {
    const sync = () => setRole(localStorage.getItem("role"));
    window.addEventListener("alllove-auth", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("alllove-auth", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  const resources = resourcesByRole(role);
  const defaultResource = resources[0]?.name ?? "supplies";

  return (
    <BrowserRouter>
      <ConfigProvider locale={ruRU} theme={showroomTheme}>
        <RefineKbarProvider>
          <Refine
            key={role ?? "guest"}
            dataProvider={dataProvider}
            authProvider={authProvider}
            routerProvider={routerProvider}
            resources={resources}
            options={{ title: { text: "AllLove" } }}
          >
            <Routes>
              <Route
                element={
                  <Authenticated key="auth" fallback={<Navigate to="/login" />}>
                    <RoleGate>
                      <AppShell />
                    </RoleGate>
                  </Authenticated>
                }
              >
                <Route index element={<NavigateToResource resource={defaultResource} />} />
                <Route path="/users" element={<UsersList />} />
                <Route path="/users/create" element={<UserCreate />} />
                <Route path="/users/edit/:id" element={<UserEdit />} />
                <Route path="/suppliers" element={<SuppliersPage />} />
                <Route path="/locations" element={<LocationsPage />} />
                <Route path="/catalog" element={<CatalogPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="/history" element={<HistoryPage />} />
                <Route path="/backups" element={<BackupsPage />} />
                <Route path="/supplies" element={<SupplyList />} />
                <Route path="/supplies/create" element={<SupplyCreate />} />
                <Route path="/supplies/:id" element={<SupplyShow />} />
                <Route path="/archive" element={<ArchivePage />} />
                <Route path="/notifications" element={<NotificationsPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/queue" element={<QueuePage />} />
                <Route path="/help" element={<HelpPage />} />
              </Route>
              <Route
                element={
                  <Authenticated key="noauth" fallback={<Login />} loading={<Login />}>
                    <NavigateToResource resource={defaultResource} />
                  </Authenticated>
                }
              >
                <Route path="/login" element={<Login />} />
              </Route>
            </Routes>
          </Refine>
        </RefineKbarProvider>
      </ConfigProvider>
    </BrowserRouter>
  );
}
