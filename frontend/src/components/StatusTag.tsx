import React from "react";
import { Tag } from "antd";
import { STATUS_COLORS, STATUS_OPTIONS } from "../constants";

export const StatusTag: React.FC<{ status: string; overdue?: boolean }> = ({ status, overdue }) => {
  const label = STATUS_OPTIONS.find((item) => item.value === status)?.label ?? status;
  return (
    <>
      <Tag color={STATUS_COLORS[status] ?? "default"}>{label}</Tag>
      {overdue ? <Tag color="volcano">Просрочена</Tag> : null}
    </>
  );
};
