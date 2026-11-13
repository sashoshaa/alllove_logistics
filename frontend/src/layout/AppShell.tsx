import React from "react";
import { useGetIdentity, useLogout } from "@refinedev/core";
import { Badge, Button, Drawer, Layout } from "antd";
import { MenuOutlined } from "@ant-design/icons";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { axiosInstance } from "../dataProvider";
import { ROLE_LABELS } from "../constants";

const { Sider, Header, Content } = Layout;

const NAV: Record<string, { to: string; label: string; badge?: boolean }[]> = {
  admin: [
    { to: "/users", label: "Люди" },
    { to: "/suppliers", label: "Поставщики" },
    { to: "/locations", label: "Места" },
    { to: "/catalog", label: "Номенклатура" },
    { to: "/audit", label: "Журнал" },
    { to: "/history", label: "История" },
    { to: "/backups", label: "Копии" },
    { to: "/help", label: "Справка" },
  ],
  client: [
    { to: "/supplies", label: "Поставки" },
    { to: "/supplies/create", label: "Новая" },
    { to: "/archive", label: "Архив" },
    { to: "/notifications", label: "Уведомления", badge: true },
    { to: "/reports", label: "Отчёты" },
    { to: "/help", label: "Справка" },
  ],
  validator: [
    { to: "/queue", label: "Очередь" },
    { to: "/notifications", label: "Уведомления", badge: true },
    { to: "/help", label: "Справка" },
  ],
};

function NavLinks({
  items,
  unread,
  onClick,
}: {
  items: { to: string; label: string; badge?: boolean }[];
  unread: number;
  onClick?: () => void;
}) {
  return (
    <nav className="shell-nav">
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} className="shell-link" onClick={onClick}>
          {item.label}
          {item.badge && unread > 0 ? <Badge count={unread} size="small" /> : null}
        </NavLink>
      ))}
    </nav>
  );
}

export const AppShell: React.FC = () => {
  const role = localStorage.getItem("role") || "client";
  const items = NAV[role] ?? NAV.client;
  const { data: identity } = useGetIdentity<{ name: string }>();
  const { mutate: logout } = useLogout();
  const [unread, setUnread] = React.useState(0);
  const [open, setOpen] = React.useState(false);
  const location = useLocation();

  React.useEffect(() => {
    void axiosInstance.get("/notifications").then(({ data }) => {
      setUnread(data.filter((item: { is_read: boolean }) => !item.is_read).length);
    });
  }, [location.pathname]);

  return (
    <Layout className="shell">
      <Sider width={240} breakpoint="lg" collapsedWidth={0} className="shell-sider" trigger={null}>
        <Link to="/" className="brand">
          <span className="brand-mark">AllLove</span>
          <span className="brand-sub">логистика шоурума</span>
        </Link>
        <NavLinks items={items} unread={unread} />
      </Sider>
      <Layout>
        <Header className="shell-header">
          <Button className="shell-menu-btn" type="text" icon={<MenuOutlined />} onClick={() => setOpen(true)} />
          <div className="shell-user">
            <span className="shell-name">{identity?.name}</span>
            <span className="shell-role">{ROLE_LABELS[role] ?? role}</span>
            <Button type="text" onClick={() => logout()}>
              Выйти
            </Button>
          </div>
        </Header>
        <Content className="shell-content">
          <Outlet />
        </Content>
      </Layout>
      <Drawer
        placement="left"
        open={open}
        onClose={() => setOpen(false)}
        width={280}
        styles={{ body: { background: "#1C1410", padding: 24 } }}
      >
        <Link to="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark">AllLove</span>
          <span className="brand-sub">логистика шоурума</span>
        </Link>
        <NavLinks items={items} unread={unread} onClick={() => setOpen(false)} />
      </Drawer>
    </Layout>
  );
};
