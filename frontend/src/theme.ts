import type { ThemeConfig } from "antd";

export const showroomTheme: ThemeConfig = {
  token: {
    colorPrimary: "#7A2E2A",
    colorInfo: "#7A2E2A",
    colorSuccess: "#4A6B4A",
    colorWarning: "#B8894A",
    colorError: "#9B2C2C",
    colorBgLayout: "#F6F1EA",
    colorBgContainer: "#FFFCF8",
    colorText: "#1C1410",
    colorTextSecondary: "#7A6A5E",
    colorBorder: "#E6D9CC",
    colorSplit: "#E6D9CC",
    borderRadius: 12,
    fontFamily: "'Manrope', sans-serif",
    fontSize: 14,
    controlHeight: 40,
  },
  components: {
    Layout: {
      bodyBg: "#F6F1EA",
      headerBg: "transparent",
      siderBg: "#1C1410",
    },
    Button: {
      primaryShadow: "none",
      fontWeight: 600,
      borderRadius: 999,
    },
    Table: {
      headerBg: "#F3EBE3",
      headerColor: "#5C4C42",
      rowHoverBg: "#F8F1E8",
    },
    Card: {
      borderRadiusLG: 18,
    },
    Menu: {
      darkItemBg: "#1C1410",
      darkItemSelectedBg: "#7A2E2A",
      darkItemHoverBg: "#2A211C",
    },
  },
};
