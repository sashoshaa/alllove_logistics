import React from "react";
import { Button, Card, DatePicker, Select, Space, Table } from "antd";
import { axiosInstance } from "../../dataProvider";
import { STATUS_OPTIONS } from "../../constants";

export const ReportsPage: React.FC = () => {
  const [registry, setRegistry] = React.useState([]);
  const [diffs, setDiffs] = React.useState([]);
  const [status, setStatus] = React.useState<string>();
  const [period, setPeriod] = React.useState<[string, string] | null>(null);

  const params = () => {
    const query: Record<string, string> = {};
    if (status) query.status = status;
    if (period) {
      query.date_from = period[0];
      query.date_to = period[1];
    }
    return query;
  };

  const load = async () => {
    const query = params();
    const [reg, disc] = await Promise.all([
      axiosInstance.get("/reports/registry", { params: query }),
      axiosInstance.get("/reports/discrepancies", { params: query }),
    ]);
    setRegistry(reg.data);
    setDiffs(disc.data);
  };

  React.useEffect(() => {
    void load();
  }, []);

  const download = async (path: string, filename: string) => {
    const response = await axiosInstance.get(path, { params: params(), responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <h1 className="page-title">Отчёты</h1>
        <p className="page-lead">Реестр поставок и расхождения. CSV совпадает с тем, что на экране.</p>
      </div>
      <Space>
        <DatePicker.RangePicker
          onChange={(_, formatted) => {
            if (formatted[0] && formatted[1]) setPeriod([formatted[0], formatted[1]]);
            else setPeriod(null);
          }}
        />
        <Select allowClear placeholder="Статус" style={{ width: 200 }} options={STATUS_OPTIONS} onChange={setStatus} />
        <Button type="primary" onClick={() => void load()}>
          Сформировать
        </Button>
      </Space>
      <Card
        title="Реестр поставок"
        extra={
          <Button onClick={() => download("/reports/registry.csv", "registry.csv")}>Выгрузить CSV</Button>
        }
      >
        <Table
          rowKey="number"
          dataSource={registry}
          columns={[
            { title: "Номер", dataIndex: "number" },
            { title: "Поставщик", dataIndex: "supplier" },
            { title: "Место", dataIndex: "destination" },
            { title: "Дата", dataIndex: "planned_date" },
            { title: "Статус", dataIndex: "status" },
            { title: "Ответственный", dataIndex: "responsible" },
            {
              title: "Просрочка",
              dataIndex: "is_overdue",
              render: (value: boolean) => (value ? "да" : "нет"),
            },
            { title: "Состав", dataIndex: "items" },
          ]}
        />
      </Card>
      <Card
        title="Отчёт о расхождениях"
        extra={
          <Button onClick={() => download("/reports/discrepancies.csv", "discrepancies.csv")}>
            Выгрузить CSV
          </Button>
        }
      >
        <Table
          rowKey={(row: { number: string; sku: string }) => `${row.number}-${row.sku}`}
          dataSource={diffs}
          columns={[
            { title: "Номер", dataIndex: "number" },
            { title: "Артикул", dataIndex: "sku" },
            { title: "Наименование", dataIndex: "name" },
            { title: "План", dataIndex: "planned_qty" },
            { title: "Факт", dataIndex: "actual_qty" },
            { title: "Разница", dataIndex: "difference" },
            { title: "Вид", dataIndex: "kind" },
            { title: "Комментарий", dataIndex: "comment" },
          ]}
        />
      </Card>
    </Space>
  );
};
