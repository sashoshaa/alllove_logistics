import React from "react";
import { useTable, useForm } from "@refinedev/antd";
import { Table, Button, Form, Input, Select, Modal, Space, Switch, message } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { axiosInstance } from "../../dataProvider";

function DirectoryTable({
  resource,
  title,
  extraFields,
}: {
  resource: string;
  title: string;
  extraFields?: React.ReactNode;
}) {
  const { tableProps, tableQuery } = useTable({ resource });
  const [open, setOpen] = React.useState(false);
  const { formProps, onFinish, form } = useForm({
    resource,
    action: "create",
    onMutationSuccess: () => {
      message.success("Запись сохранена");
      setOpen(false);
      form.resetFields();
      tableQuery.refetch();
    },
  });

  const toggle = async (id: number, is_active: boolean) => {
    await axiosInstance.patch(`/${resource}/${id}`, { is_active: !is_active });
    tableQuery.refetch();
  };

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          Добавить
        </Button>
      </Space>
      <Table {...tableProps} rowKey="id">
        <Table.Column dataIndex="id" title="ID" width={70} />
        {resource === "catalog" ? <Table.Column dataIndex="sku" title="Артикул" /> : null}
        <Table.Column dataIndex="name" title="Наименование" />
        {resource === "suppliers" ? <Table.Column dataIndex="contact" title="Контакт" /> : null}
        {resource === "locations" ? (
          <Table.Column
            dataIndex="type"
            title="Тип"
            render={(value: string) => (value === "showroom" ? "Шоурум" : "Склад")}
          />
        ) : null}
        {resource === "catalog" ? <Table.Column dataIndex="category" title="Категория" /> : null}
        {resource === "catalog" ? <Table.Column dataIndex="size" title="Размер" /> : null}
        {resource === "catalog" ? <Table.Column dataIndex="color" title="Цвет" /> : null}
        <Table.Column dataIndex="address" title="Адрес" />
        <Table.Column
          dataIndex="is_active"
          title="Активна"
          render={(value: boolean, record: { id: number; is_active: boolean }) => (
            <Switch checked={value} onChange={() => toggle(record.id, record.is_active)} />
          )}
        />
      </Table>
      <Modal
        title={title}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText="Сохранить"
      >
        <Form {...formProps} layout="vertical" onFinish={onFinish}>
          {resource === "catalog" ? (
            <Form.Item label="Артикул" name="sku" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          ) : null}
          <Form.Item label="Наименование" name="name" rules={[{ required: true, min: 2 }]}>
            <Input />
          </Form.Item>
          {extraFields}
        </Form>
      </Modal>
    </>
  );
}

export const SuppliersPage: React.FC = () => (
  <DirectoryTable
    resource="suppliers"
    title="Поставщик"
    extraFields={
      <>
        <Form.Item label="Контакт" name="contact">
          <Input />
        </Form.Item>
        <Form.Item label="Адрес" name="address">
          <Input />
        </Form.Item>
      </>
    }
  />
);

export const LocationsPage: React.FC = () => (
  <DirectoryTable
    resource="locations"
    title="Место назначения"
    extraFields={
      <>
        <Form.Item label="Тип" name="type" rules={[{ required: true }]} initialValue="warehouse">
          <Select
            options={[
              { value: "warehouse", label: "Склад" },
              { value: "showroom", label: "Шоурум" },
            ]}
          />
        </Form.Item>
        <Form.Item label="Адрес" name="address">
          <Input />
        </Form.Item>
      </>
    }
  />
);

export const CatalogPage: React.FC = () => (
  <DirectoryTable
    resource="catalog"
    title="Позиция номенклатуры"
    extraFields={
      <>
        <Form.Item label="Категория" name="category">
          <Input />
        </Form.Item>
        <Form.Item label="Размер" name="size">
          <Input />
        </Form.Item>
        <Form.Item label="Цвет" name="color">
          <Input />
        </Form.Item>
      </>
    }
  />
);
