import React from "react";
import { Button, Popconfirm, Space, Table, message } from "antd";
import { axiosInstance } from "../../dataProvider";

interface BackupRow {
  name: string;
  path: string;
  has_database: boolean;
  has_documents: boolean;
}

export const BackupsPage: React.FC = () => {
  const [rows, setRows] = React.useState<BackupRow[]>([]);

  const load = React.useCallback(async () => {
    const { data } = await axiosInstance.get("/admin/backups");
    setRows(data);
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const createCopy = async () => {
    await axiosInstance.post("/admin/backups");
    message.success("Копия создана");
    await load();
  };

  const restore = async (name: string) => {
    await axiosInstance.post(`/admin/backups/${name}/restore`);
    message.success(`Восстановлено из ${name}`);
    await load();
  };

  return (
    <>
      <h1 className="page-title">Копии</h1>
      <p className="page-lead">Ежедневный комплект базы и файлов. Хранятся последние семь копий.</p>
      <Button type="primary" onClick={() => void createCopy()} style={{ marginBottom: 16 }}>
        Сделать копию сейчас
      </Button>
      <Table
        rowKey="name"
        dataSource={rows}
        columns={[
          { title: "Дата", dataIndex: "name" },
          {
            title: "База",
            dataIndex: "has_database",
            render: (value: boolean) => (value ? "есть" : "нет"),
          },
          {
            title: "Файлы",
            dataIndex: "has_documents",
            render: (value: boolean) => (value ? "есть" : "нет"),
          },
          {
            title: "",
            render: (_: unknown, record: BackupRow) => (
              <Space>
                <Popconfirm
                  title="Восстановить эту копию? Текущие данные будут заменены."
                  onConfirm={() => void restore(record.name)}
                >
                  <Button>Восстановить</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
    </>
  );
};
