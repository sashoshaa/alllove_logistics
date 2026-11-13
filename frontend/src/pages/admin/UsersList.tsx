import React from "react";
import { useTable } from "@refinedev/antd";
import { Table, Space, Button, Tag, Switch, message } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { Link } from "react-router";
import { axiosInstance } from "../../dataProvider";
import { ROLE_LABELS } from "../../constants";
import type { User } from "../../types";

export const UsersList: React.FC = () => {
  const { tableProps, tableQuery } = useTable<User>({ resource: "users" });

  const toggleActive = async (user: User) => {
    await axiosInstance.patch(`/users/${user.id}`, { is_active: !user.is_active });
    message.success(user.is_active ? "Доступ заблокирован" : "Доступ открыт");
    tableQuery.refetch();
  };

  return (
    <>
      <h1 className="page-title">Люди</h1>
      <p className="page-lead">Учётные записи не удаляются: доступ блокируется, чтобы сохранить историю.</p>
      <Space style={{ marginBottom: 16 }}>
        <Link to="/users/create">
          <Button type="primary" icon={<PlusOutlined />}>
            Создать пользователя
          </Button>
        </Link>
      </Space>
      <Table {...tableProps} rowKey="id">
        <Table.Column dataIndex="id" title="ID" width={70} />
        <Table.Column dataIndex="email" title="Email" />
        <Table.Column dataIndex="full_name" title="ФИО" />
        <Table.Column dataIndex="phone" title="Контакт" />
        <Table.Column
          dataIndex="role"
          title="Роль"
          render={(role: string) => ROLE_LABELS[role] ?? role}
        />
        <Table.Column
          dataIndex="is_active"
          title="Доступ"
          render={(value: boolean, record: User) => (
            <Switch checked={value} onChange={() => toggleActive(record)} />
          )}
        />
        <Table.Column
          title=""
          render={(_: unknown, record: User) => (
            <Space>
              <Link to={`/users/edit/${record.id}`}>Изменить</Link>
              <Tag color={record.is_active ? "green" : "red"}>
                {record.is_active ? "Активен" : "Заблокирован"}
              </Tag>
            </Space>
          )}
        />
      </Table>
    </>
  );
};
