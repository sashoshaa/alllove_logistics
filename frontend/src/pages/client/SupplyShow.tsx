import React from "react";
import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  List,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Upload,
  message,
} from "antd";
import type { UploadProps } from "antd";
import { useNavigate, useParams } from "react-router";
import dayjs from "dayjs";
import { axiosInstance } from "../../dataProvider";
import { StatusTag } from "../../components/StatusTag";
import type { DocumentFile, StorageLocation, Supplier, Supply, User } from "../../types";

interface HistoryRow {
  id: number;
  actor_name?: string;
  source: string;
  field: string;
  old_value?: string;
  new_value?: string;
  created_at: string;
}

interface CommentRow {
  id: number;
  author_name?: string;
  text: string;
  created_at: string;
}

interface ProposalRow {
  id: number;
  author_name?: string;
  payload: Record<string, unknown>;
  status: string;
  comment?: string;
  created_at: string;
}

export const SupplyShow: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const role = localStorage.getItem("role");
  const userId = Number(localStorage.getItem("user_id") || 0);
  const [supply, setSupply] = React.useState<Supply>();
  const [history, setHistory] = React.useState<HistoryRow[]>([]);
  const [comments, setComments] = React.useState<CommentRow[]>([]);
  const [proposals, setProposals] = React.useState<ProposalRow[]>([]);
  const [commentText, setCommentText] = React.useState("");
  const [editing, setEditing] = React.useState(false);
  const [editForm] = Form.useForm();
  const [proposalForm] = Form.useForm();
  const [suppliers, setSuppliers] = React.useState<Supplier[]>([]);
  const [locations, setLocations] = React.useState<StorageLocation[]>([]);
  const [people, setPeople] = React.useState<User[]>([]);
  const canEdit =
    role === "client" && ["created", "in_transit", "has_discrepancies"].includes(supply?.status ?? "");

  const load = React.useCallback(async () => {
    if (!id) return;
    const [card, hist, comm, props] = await Promise.all([
      axiosInstance.get(`/supplies/${id}`),
      axiosInstance.get(`/supplies/${id}/history`),
      axiosInstance.get(`/supplies/${id}/comments`),
      axiosInstance.get(`/supplies/${id}/proposals`),
    ]);
    setSupply(card.data);
    setHistory(hist.data);
    setComments(comm.data);
    setProposals(props.data);
  }, [id]);

  React.useEffect(() => {
    void load();
    void Promise.all([
      axiosInstance.get("/suppliers"),
      axiosInstance.get("/locations"),
      axiosInstance.get("/users"),
    ]).then(([s, l, u]) => {
      setSuppliers(s.data);
      setLocations(l.data);
      setPeople(u.data.filter((item: User) => item.role === "client" && item.is_active));
    });
  }, [load]);

  if (!supply) return null;

  const changeStatus = async (status: string) => {
    try {
      await axiosInstance.post(`/supplies/${supply.id}/status`, { status });
      message.success("Статус обновлён");
      await load();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "Нельзя сменить статус");
    }
  };

  const addComment = async () => {
    try {
      await axiosInstance.post(`/supplies/${supply.id}/comments`, { text: commentText });
      setCommentText("");
      await load();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "Комментарий не сохранён");
    }
  };

  const sendProposal = async (values: { planned_date?: dayjs.Dayjs; comment?: string }) => {
    try {
      await axiosInstance.post(`/supplies/${supply.id}/proposals`, {
        planned_date: values.planned_date?.format("YYYY-MM-DD"),
        comment: values.comment,
      });
      message.success("Предложение отправлено");
      proposalForm.resetFields();
      await load();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "Не удалось отправить предложение");
    }
  };

  const decide = async (proposalId: number, accept: boolean) => {
    try {
      await axiosInstance.post(`/proposals/${proposalId}/${accept ? "accept" : "reject"}`);
      message.success(accept ? "Предложение принято" : "Предложение отклонено");
      await load();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "Действие недоступно");
    }
  };

  const saveEdit = async (values: {
    supplier_id: number;
    location_id: number;
    planned_date: dayjs.Dayjs;
    responsible_id: number;
  }) => {
    try {
      await axiosInstance.patch(`/supplies/${supply.id}`, {
        supplier_id: values.supplier_id,
        location_id: values.location_id,
        planned_date: values.planned_date.format("YYYY-MM-DD"),
        responsible_id: values.responsible_id,
      });
      message.success("Поставка сохранена");
      setEditing(false);
      await load();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "Не удалось сохранить");
    }
  };

  const uploadProps: UploadProps = {
    customRequest: async (options) => {
      const form = new FormData();
      form.append("file", options.file as File);
      try {
        await axiosInstance.post(`/supplies/${supply.id}/documents`, form);
        options.onSuccess?.(null);
        message.success("Файл загружен");
        await load();
      } catch {
        options.onError?.(new Error("upload"));
        message.error("Файл не принят. Нужны PDF, JPG или PNG до 20 МБ.");
      }
    },
    showUploadList: false,
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <h1 className="page-title">{supply.number}</h1>
        <p className="page-lead">Карточка партии: состав, документы, предложения и история.</p>
      </div>
      <Card
        extra={
          <Space wrap>
            <StatusTag status={supply.status} overdue={supply.is_overdue} />
            {canEdit ? (
              <Button
                onClick={() => {
                  editForm.setFieldsValue({
                    supplier_id: supply.supplier_id,
                    location_id: supply.location_id,
                    planned_date: dayjs(supply.planned_date),
                    responsible_id: supply.responsible_id,
                  });
                  setEditing(true);
                }}
              >
                Изменить
              </Button>
            ) : null}
            {role === "client" ? (
              <Button onClick={() => navigate(`/supplies/create?from=${supply.id}`)}>Повторить</Button>
            ) : null}
          </Space>
        }
      >
        <Descriptions column={2}>
          <Descriptions.Item label="Поставщик">{supply.supplier_name}</Descriptions.Item>
          <Descriptions.Item label="Место">{supply.location_name}</Descriptions.Item>
          <Descriptions.Item label="Плановая дата">{supply.planned_date}</Descriptions.Item>
          <Descriptions.Item label="Ответственный">{supply.responsible_name}</Descriptions.Item>
          <Descriptions.Item label="Создатель">{supply.created_by_name}</Descriptions.Item>
          {supply.is_overdue ? (
            <Descriptions.Item label="Просрочка">{supply.overdue_days} дн.</Descriptions.Item>
          ) : null}
        </Descriptions>
        {role === "client" ? (
          <Space wrap style={{ marginTop: 16 }}>
            {supply.status === "created" ? (
              <Button onClick={() => changeStatus("in_transit")}>В путь</Button>
            ) : null}
            {supply.status === "in_transit" ? (
              <Button type="primary" onClick={() => changeStatus("on_check")}>
                На проверку
              </Button>
            ) : null}
            {supply.status === "checked" ? (
              <Button type="primary" onClick={() => changeStatus("completed")}>
                Завершить
              </Button>
            ) : null}
            {["created", "in_transit", "has_discrepancies"].includes(supply.status) ? (
              <Button danger onClick={() => changeStatus("cancelled")}>
                Отменить
              </Button>
            ) : null}
          </Space>
        ) : null}
      </Card>

      <Tabs
        items={[
          {
            key: "items",
            label: "Состав",
            children: (
              <Table
                rowKey="id"
                dataSource={supply.items}
                pagination={false}
                columns={[
                  { title: "Артикул", dataIndex: "sku" },
                  { title: "Наименование", dataIndex: "name" },
                  { title: "Размер", dataIndex: "size" },
                  { title: "Цвет", dataIndex: "color" },
                  { title: "План", dataIndex: "planned_qty" },
                  { title: "Факт", dataIndex: "actual_qty" },
                  { title: "Разница", dataIndex: "difference" },
                ]}
              />
            ),
          },
          {
            key: "docs",
            label: "Документы",
            children: (
              <Space direction="vertical" style={{ width: "100%" }}>
                {role === "client" ? (
                  <Upload {...uploadProps}>
                    <Button>Прикрепить документ</Button>
                  </Upload>
                ) : null}
                <List
                  dataSource={supply.documents}
                  renderItem={(item: DocumentFile) => (
                    <List.Item>
                      <a
                        href={`/api/documents/${item.id}/download`}
                        onClick={async (event) => {
                          event.preventDefault();
                          const response = await axiosInstance.get(`/documents/${item.id}/download`, {
                            responseType: "blob",
                          });
                          const url = URL.createObjectURL(response.data);
                          const link = document.createElement("a");
                          link.href = url;
                          link.download = item.original_name;
                          link.click();
                        }}
                      >
                        {item.original_name}
                      </a>
                    </List.Item>
                  )}
                />
              </Space>
            ),
          },
          {
            key: "comments",
            label: "Комментарии",
            children: (
              <Space direction="vertical" style={{ width: "100%" }}>
                <List
                  dataSource={comments}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        title={`${item.author_name} · ${item.created_at}`}
                        description={item.text}
                      />
                    </List.Item>
                  )}
                />
                <Input.TextArea
                  value={commentText}
                  onChange={(event) => setCommentText(event.target.value)}
                  rows={3}
                  placeholder="Комментарий не меняет состав и статус"
                />
                <Button onClick={addComment}>Добавить комментарий</Button>
              </Space>
            ),
          },
          {
            key: "proposals",
            label: "Предложения",
            children: (
              <Space direction="vertical" style={{ width: "100%" }}>
                {role === "client" ? (
                  <Form form={proposalForm} layout="inline" onFinish={sendProposal}>
                    <Form.Item name="planned_date" rules={[{ required: true, message: "Укажите новую дату" }]}>
                      <DatePicker placeholder="Новая плановая дата" />
                    </Form.Item>
                    <Form.Item name="comment">
                      <Input placeholder="Комментарий" />
                    </Form.Item>
                    <Button htmlType="submit">Предложить изменение</Button>
                  </Form>
                ) : null}
                <Table
                  rowKey="id"
                  dataSource={proposals}
                  pagination={false}
                  columns={[
                    { title: "Автор", dataIndex: "author_name" },
                    { title: "Данные", dataIndex: "payload", render: (value) => JSON.stringify(value) },
                    { title: "Статус", dataIndex: "status" },
                    {
                      title: "",
                      render: (_: unknown, record: ProposalRow) =>
                        role === "client" &&
                        record.status === "pending" &&
                        userId === supply.responsible_id ? (
                          <Space>
                            <Button size="small" type="primary" onClick={() => decide(record.id, true)}>
                              Принять
                            </Button>
                            <Button size="small" onClick={() => decide(record.id, false)}>
                              Отклонить
                            </Button>
                          </Space>
                        ) : null,
                    },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: "history",
            label: "История",
            children: (
              <Table
                rowKey="id"
                dataSource={history}
                pagination={false}
                columns={[
                  { title: "Время", dataIndex: "created_at" },
                  { title: "Автор", dataIndex: "actor_name" },
                  { title: "Источник", dataIndex: "source" },
                  { title: "Поле", dataIndex: "field" },
                  { title: "Было", dataIndex: "old_value" },
                  { title: "Стало", dataIndex: "new_value" },
                ]}
              />
            ),
          },
        ]}
      />
      <Modal
        title="Изменение поставки"
        open={editing}
        onCancel={() => setEditing(false)}
        onOk={() => editForm.submit()}
        okText="Сохранить"
      >
        <Form form={editForm} layout="vertical" onFinish={saveEdit}>
          <Form.Item name="supplier_id" label="Поставщик" rules={[{ required: true }]}>
            <Select options={suppliers.map((item) => ({ value: item.id, label: item.name }))} />
          </Form.Item>
          <Form.Item name="location_id" label="Место" rules={[{ required: true }]}>
            <Select options={locations.map((item) => ({ value: item.id, label: item.name }))} />
          </Form.Item>
          <Form.Item name="planned_date" label="Плановая дата" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="responsible_id" label="Ответственный" rules={[{ required: true }]}>
            <Select options={people.map((item) => ({ value: item.id, label: item.full_name }))} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};
