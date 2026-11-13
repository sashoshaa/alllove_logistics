import React from "react";
import { Button, Card, Descriptions, Input, InputNumber, Space, Table, message } from "antd";
import { axiosInstance } from "../../dataProvider";
import { StatusTag } from "../../components/StatusTag";
import type { Supply } from "../../types";

export const QueuePage: React.FC = () => {
  const [queue, setQueue] = React.useState<Supply[]>([]);
  const [current, setCurrent] = React.useState<Supply>();
  const [facts, setFacts] = React.useState<Record<number, number | null>>({});
  const [comment, setComment] = React.useState("");
  const [loading, setLoading] = React.useState(true);

  const openSupply = React.useCallback(async (id: number) => {
    const { data } = await axiosInstance.get(`/supplies/${id}`);
    setCurrent(data);
    const initial: Record<number, number | null> = {};
    for (const item of data.items ?? []) initial[item.id] = item.actual_qty;
    setFacts(initial);
  }, []);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axiosInstance.get("/supplies");
      const rows: Supply[] = Array.isArray(data) ? data : [];
      setQueue(rows);
      if (rows[0]) {
        await openSupply(rows[0].id);
      } else {
        setCurrent(undefined);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "Не удалось загрузить очередь проверки");
      setQueue([]);
      setCurrent(undefined);
    } finally {
      setLoading(false);
    }
  }, [openSupply]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const allFilled = current?.items?.every((item) => facts[item.id] !== undefined && facts[item.id] !== null);
  const hasDiff = current?.items?.some((item) => {
    const actual = facts[item.id];
    if (actual === undefined || actual === null) return false;
    return Number(actual) !== item.planned_qty;
  });

  const submit = async (returnBack = false) => {
    if (!current) return;
    try {
      await axiosInstance.post(`/supplies/${current.id}/check`, {
        items: current.items.map((item) => ({
          item_id: item.id,
          actual_qty: Number(facts[item.id] ?? 0),
        })),
        comment,
        return_for_clarification: returnBack,
      });
      message.success("Результат проверки сохранён");
      setComment("");
      await load();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "Проверку нельзя подтвердить");
    }
  };

  return (
    <>
      <h1 className="page-title">Очередь проверки</h1>
      <p className="page-lead">Только поставки «На проверке». Просроченные строки выделены.</p>
      <div className="queue-wrap">
      <Card title="Ожидают сверки">
        <Table
          rowKey="id"
          size="small"
          dataSource={queue}
          loading={loading}
          pagination={false}
          onRow={(record) => ({ onClick: () => void openSupply(record.id) })}
          rowClassName={(record) => (record.is_overdue ? "overdue-row" : "")}
          columns={[
            { title: "Номер", dataIndex: "number" },
            {
              title: "Срок",
              render: (_: unknown, record: Supply) => (
                <StatusTag status={record.status} overdue={record.is_overdue} />
              ),
            },
          ]}
        />
      </Card>
      {current ? (
        <Card title={`Проверка ${current.number}`} style={{ flex: 1 }}>
          <Descriptions column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="Поставщик">{current.supplier_name}</Descriptions.Item>
            <Descriptions.Item label="Место">{current.location_name}</Descriptions.Item>
            <Descriptions.Item label="План">{current.planned_date}</Descriptions.Item>
            <Descriptions.Item label="Ответственный">{current.responsible_name}</Descriptions.Item>
          </Descriptions>
          <Space direction="vertical" style={{ marginBottom: 16 }}>
            {(current.documents ?? []).map((doc) => (
              <a
                key={doc.id}
                href={`/api/documents/${doc.id}/download`}
                onClick={async (event) => {
                  event.preventDefault();
                  const response = await axiosInstance.get(`/documents/${doc.id}/download`, {
                    responseType: "blob",
                  });
                  const url = URL.createObjectURL(response.data);
                  const link = document.createElement("a");
                  link.href = url;
                  link.download = doc.original_name;
                  link.click();
                }}
              >
                {doc.original_name}
              </a>
            ))}
          </Space>
          <Table
            rowKey="id"
            pagination={false}
            dataSource={current.items ?? []}
            columns={[
              { title: "Артикул", dataIndex: "sku" },
              { title: "Наименование", dataIndex: "name" },
              { title: "План", dataIndex: "planned_qty" },
              {
                title: "Факт",
                render: (_: unknown, record) => (
                  <InputNumber
                    min={0}
                    value={facts[record.id] ?? undefined}
                    onChange={(value) => setFacts((prev) => ({ ...prev, [record.id]: value }))}
                  />
                ),
              },
              {
                title: "Разница",
                render: (_: unknown, record) => {
                  const actual = facts[record.id];
                  if (actual === undefined || actual === null) return "";
                  const diff = Number(actual) - record.planned_qty;
                  if (diff === 0) return "совпало";
                  return diff > 0 ? `излишек ${diff}` : `недостача ${Math.abs(diff)}`;
                },
              },
            ]}
          />
          <Input.TextArea
            style={{ marginTop: 16 }}
            rows={3}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder="Комментарий к результату проверки"
          />
          <Space style={{ marginTop: 16 }}>
            <Button onClick={() => void submit(true)}>Вернуть на уточнение</Button>
            <Button type="primary" disabled={!allFilled} onClick={() => void submit(false)}>
              {hasDiff ? "Зафиксировать расхождения" : "Подтвердить проверку"}
            </Button>
          </Space>
        </Card>
      ) : (
        <Card>{loading ? "Загрузка очереди…" : "Нет поставок в очереди"}</Card>
      )}
      </div>
    </>
  );
};
