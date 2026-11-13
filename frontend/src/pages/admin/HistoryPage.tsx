import React from "react";
import { Button, Input, Table } from "antd";
import { axiosInstance } from "../../dataProvider";
import { StatusTag } from "../../components/StatusTag";
import type { Supply } from "../../types";

interface HistoryRow {
  id: number;
  actor_name?: string;
  source: string;
  field: string;
  old_value?: string;
  new_value?: string;
  created_at: string;
}

export const HistoryPage: React.FC = () => {
  const [query, setQuery] = React.useState("");
  const [rows, setRows] = React.useState<Supply[]>([]);
  const [current, setCurrent] = React.useState<Supply>();
  const [history, setHistory] = React.useState<HistoryRow[]>([]);

  const search = async (value = query) => {
    const { data } = await axiosInstance.get("/supplies", {
      params: { search: value, sort: "id", order: "desc", limit: 50 },
    });
    setRows(data);
    if (data[0]) {
      await openSupply(data[0].id);
    } else {
      setCurrent(undefined);
      setHistory([]);
    }
  };

  const openSupply = async (id: number) => {
    const [card, events] = await Promise.all([
      axiosInstance.get(`/supplies/${id}`),
      axiosInstance.get(`/supplies/${id}/history`),
    ]);
    setCurrent(card.data);
    setHistory(events.data);
  };

  React.useEffect(() => {
    void search("");
  }, []);

  return (
    <>
      <h1 className="page-title">История поставки</h1>
      <p className="page-lead">Администратор выбирает поставку и видит, кто и откуда изменил поля. Журнал рядом не правится.</p>
      <div className="toolbar">
        <Input.Search
          placeholder="Номер или артикул"
          allowClear
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onSearch={(value) => void search(value)}
          style={{ width: 280 }}
        />
        <Button onClick={() => void search(query)}>Найти</Button>
      </div>
      <Table
        rowKey="id"
        size="small"
        dataSource={rows}
        pagination={{ pageSize: 8 }}
        onRow={(record) => ({ onClick: () => void openSupply(record.id), className: "click-row" })}
        columns={[
          { title: "Номер", dataIndex: "number" },
          { title: "Статус", render: (_: unknown, record: Supply) => <StatusTag status={record.status} overdue={record.is_overdue} /> },
          { title: "Ответственный", dataIndex: "responsible_name" },
        ]}
        style={{ marginBottom: 24 }}
      />
      {current ? (
        <>
          <h2 className="page-lead" style={{ fontFamily: "Cormorant Garamond, serif", fontSize: 28, color: "#1c1410" }}>
            {current.number}
          </h2>
          <Table
            rowKey="id"
            dataSource={history}
            pagination={false}
            columns={[
              { title: "Время", dataIndex: "created_at" },
              { title: "Кто", dataIndex: "actor_name" },
              { title: "Источник", dataIndex: "source" },
              { title: "Поле", dataIndex: "field" },
              { title: "Было", dataIndex: "old_value" },
              { title: "Стало", dataIndex: "new_value" },
            ]}
          />
        </>
      ) : (
        <p className="page-lead">Нет поставок для просмотра истории.</p>
      )}
    </>
  );
};
