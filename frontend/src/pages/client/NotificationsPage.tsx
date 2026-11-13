import React from "react";
import { Button, List, Tag } from "antd";
import { useNavigate } from "react-router";
import { axiosInstance } from "../../dataProvider";
import type { NotificationItem } from "../../types";

export const NotificationsPage: React.FC = () => {
  const [items, setItems] = React.useState<NotificationItem[]>([]);
  const navigate = useNavigate();

  const load = React.useCallback(async () => {
    const { data } = await axiosInstance.get("/notifications");
    setItems(data);
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const openItem = async (item: NotificationItem) => {
    if (!item.is_read) {
      await axiosInstance.patch(`/notifications/${item.id}/read`);
    }
    if (item.supply_id) {
      navigate(`/supplies/${item.supply_id}`);
    } else {
      await load();
    }
  };

  return (
    <>
      <h1 className="page-title">Уведомления</h1>
      <p className="page-lead">Смена статуса, проверка, предложение и просрочка. Прочитанные остаются в списке.</p>
    <List
      dataSource={items}
      locale={{ emptyText: "Нет уведомлений" }}
      renderItem={(item) => (
        <List.Item
          actions={[
            <Button key="open" type="link" onClick={() => openItem(item)}>
              Открыть
            </Button>,
          ]}
        >
          <List.Item.Meta
            title={
              <>
                {item.title} {!item.is_read ? <Tag color="blue">новое</Tag> : <Tag>прочитано</Tag>}
              </>
            }
            description={`${item.message} · ${item.created_at}`}
          />
        </List.Item>
      )}
    />
    </>
  );
};
