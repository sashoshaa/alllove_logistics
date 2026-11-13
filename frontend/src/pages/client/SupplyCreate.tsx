import React from "react";
import { Button, Card, DatePicker, Form, InputNumber, Select, Space, message } from "antd";
import { MinusCircleOutlined, PlusOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router";
import dayjs from "dayjs";
import { axiosInstance } from "../../dataProvider";
import type { CatalogItem, StorageLocation, Supplier, User } from "../../types";

export const SupplyCreate: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [suppliers, setSuppliers] = React.useState<Supplier[]>([]);
  const [locations, setLocations] = React.useState<StorageLocation[]>([]);
  const [catalog, setCatalog] = React.useState<CatalogItem[]>([]);
  const [users, setUsers] = React.useState<User[]>([]);

  React.useEffect(() => {
    void Promise.all([
      axiosInstance.get("/suppliers"),
      axiosInstance.get("/locations"),
      axiosInstance.get("/catalog"),
      axiosInstance.get("/users"),
    ]).then(([s, l, c, u]) => {
      setSuppliers(s.data);
      setLocations(l.data);
      setCatalog(c.data);
      setUsers(u.data.filter((item: User) => item.role === "client" && item.is_active));
    });
  }, []);

  React.useEffect(() => {
    const from = params.get("from");
    if (!from) return;
    void axiosInstance.get(`/supplies/${from}`).then(({ data }) => {
      form.setFieldsValue({
        supplier_id: data.supplier_id,
        location_id: data.location_id,
        items: data.items.map((item: { catalog_item_id: number; planned_qty: number }) => ({
          catalog_item_id: item.catalog_item_id,
          quantity: item.planned_qty,
        })),
      });
    });
  }, [params, form]);

  const onFinish = async (values: {
    supplier_id: number;
    location_id: number;
    planned_date: dayjs.Dayjs;
    responsible_id: number;
    items: { catalog_item_id: number; quantity: number }[];
  }) => {
    try {
      const { data } = await axiosInstance.post("/supplies", {
        supplier_id: values.supplier_id,
        location_id: values.location_id,
        planned_date: values.planned_date.format("YYYY-MM-DD"),
        responsible_id: values.responsible_id,
        items: values.items,
      });
      message.success(`Создана поставка ${data.number}`);
      navigate(`/supplies/${data.id}`);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "Не удалось создать поставку");
    }
  };

  return (
    <>
    <h1 className="page-title">Новая поставка</h1>
    <p className="page-lead">Поставщик, место и артикулы выбираются из справочника. Даты и файлы для повтора задаются заново.</p>
    <Card style={{ maxWidth: 800 }}>
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item label="Поставщик" name="supplier_id" rules={[{ required: true, message: "Выберите поставщика" }]}>
          <Select options={suppliers.map((item) => ({ value: item.id, label: item.name }))} />
        </Form.Item>
        <Form.Item label="Место назначения" name="location_id" rules={[{ required: true, message: "Выберите место" }]}>
          <Select
            options={locations.map((item) => ({
              value: item.id,
              label: `${item.name} (${item.type === "showroom" ? "шоурум" : "склад"})`,
            }))}
          />
        </Form.Item>
        <Form.Item label="Плановая дата прибытия" name="planned_date" rules={[{ required: true, message: "Укажите дату" }]}>
          <DatePicker style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item label="Ответственный" name="responsible_id" rules={[{ required: true, message: "Назначьте ответственного" }]}>
          <Select options={users.map((item) => ({ value: item.id, label: item.full_name }))} />
        </Form.Item>
        <Form.List
          name="items"
          rules={[
            {
              validator: async (_, value) => {
                if (!value || value.length < 1) {
                  return Promise.reject(new Error("Добавьте хотя бы одну позицию"));
                }
              },
            },
          ]}
        >
          {(fields, { add, remove }) => (
            <>
              {fields.map((field) => (
                <Space key={field.key} align="baseline">
                  <Form.Item
                    {...field}
                    name={[field.name, "catalog_item_id"]}
                    rules={[{ required: true, message: "Выберите артикул" }]}
                  >
                    <Select
                      style={{ width: 360 }}
                      placeholder="Номенклатура"
                      options={catalog.map((item) => ({
                        value: item.id,
                        label: `${item.sku} — ${item.name} (${item.size ?? "-"}, ${item.color ?? "-"})`,
                      }))}
                    />
                  </Form.Item>
                  <Form.Item
                    {...field}
                    name={[field.name, "quantity"]}
                    rules={[{ required: true, message: "Количество" }]}
                  >
                    <InputNumber min={1} placeholder="Кол-во" />
                  </Form.Item>
                  <MinusCircleOutlined onClick={() => remove(field.name)} />
                </Space>
              ))}
              <Button type="dashed" onClick={() => add()} icon={<PlusOutlined />} block>
                Добавить позицию
              </Button>
            </>
          )}
        </Form.List>
        <Button type="primary" htmlType="submit" style={{ marginTop: 16 }}>
          Сохранить
        </Button>
      </Form>
    </Card>
    </>
  );
};
