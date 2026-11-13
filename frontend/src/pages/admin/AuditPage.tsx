import React from "react";
import { Input, Select, Table } from "antd";
import { axiosInstance } from "../../dataProvider";

interface AuditRow {
  id: number;
  created_at: string;
  actor_name?: string | null;
  action: string;
  object_type: string;
  object_id?: number | null;
  details?: string | null;
}

export const AuditPage: React.FC = () => {
  const [rows, setRows] = React.useState<AuditRow[]>([]);
  const [objectType, setObjectType] = React.useState<string>();
  const [objectId, setObjectId] = React.useState<string>("");

  const load = React.useCallback(async () => {
    const params: Record<string, string> = {};
    if (objectType) params.object_type = objectType;
    if (objectId.trim()) params.object_id = objectId.trim();
    const { data } = await axiosInstance.get("/admin/audit", { params });
    setRows(data);
  }, [objectType, objectId]);

  React.useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <h1 className="page-title">Журнал</h1>
      <p className="page-lead">Записи нельзя изменить или удалить из интерфейса. Можно сузить по типу объекта и его ID.</p>
      <div className="toolbar">
        <Select
          allowClear
          placeholder="Тип объекта"
          style={{ width: 200 }}
          value={objectType}
          onChange={setObjectType}
          options={[
            { value: "user", label: "Пользователь" },
            { value: "supply", label: "Поставка" },
            { value: "supplier", label: "Поставщик" },
            { value: "document", label: "Документ" },
          ]}
        />
        <Input
          placeholder="ID объекта"
          style={{ width: 160 }}
          value={objectId}
          onChange={(event) => setObjectId(event.target.value)}
        />
      </div>
      <Table rowKey="id" dataSource={rows}>
        <Table.Column dataIndex="created_at" title="Время" />
        <Table.Column dataIndex="actor_name" title="Кто" />
        <Table.Column dataIndex="action" title="Действие" />
        <Table.Column dataIndex="object_type" title="Объект" />
        <Table.Column dataIndex="object_id" title="ID" />
        <Table.Column dataIndex="details" title="Детали" ellipsis />
      </Table>
    </>
  );
};
