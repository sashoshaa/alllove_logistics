import React from "react";
import { useForm } from "@refinedev/antd";
import { Form, Input, Select, Button, Card, Switch, message } from "antd";
import { useNavigate } from "react-router";

export const UserEdit: React.FC = () => {
  const navigate = useNavigate();
  const { onFinish, formProps } = useForm({
    resource: "users",
    action: "edit",
    onMutationSuccess: () => {
      message.success("Пользователь сохранён");
      navigate("/users");
    },
  });

  return (
    <Card title="Изменение пользователя" style={{ maxWidth: 640 }}>
      <Form {...formProps} layout="vertical" onFinish={onFinish}>
        <Form.Item label="Email">
          <Input value={formProps.initialValues?.email} disabled />
        </Form.Item>
        <Form.Item label="ФИО" name="full_name" rules={[{ required: true, min: 2 }]}>
          <Input />
        </Form.Item>
        <Form.Item label="Контакт" name="phone">
          <Input />
        </Form.Item>
        <Form.Item label="Роль" name="role" rules={[{ required: true }]}>
          <Select
            options={[
              { value: "client", label: "Клиент (сотрудник шоурума)" },
              { value: "validator", label: "Валидатор" },
              { value: "admin", label: "Администратор" },
            ]}
          />
        </Form.Item>
        <Form.Item label="Доступ открыт" name="is_active" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item label="Новый пароль" name="password">
          <Input.Password placeholder="Оставьте пустым, чтобы не менять" />
        </Form.Item>
        <Button type="primary" htmlType="submit">
          Сохранить
        </Button>
      </Form>
    </Card>
  );
};
