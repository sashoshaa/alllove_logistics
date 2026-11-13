import React from "react";
import { Button, DatePicker, Input, Select, Table } from "antd";
import { Link, useNavigate } from "react-router";
import type { Dayjs } from "dayjs";
import { axiosInstance } from "../../dataProvider";
import { StatusTag } from "../../components/StatusTag";
import { STATUS_OPTIONS } from "../../constants";
import type { StorageLocation, Supplier, Supply, User } from "../../types";

interface Summary {
  in_transit: number;
  on_check: number;
  overdue: number;
  completed: number;
  total: number;
}

export const SupplyList: React.FC<{ archive?: boolean }> = ({ archive = false }) => {
  const navigate = useNavigate();
  const [rows, setRows] = React.useState<Supply[]>([]);
  const [summary, setSummary] = React.useState<Summary>();
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState<string>();
  const [supplierId, setSupplierId] = React.useState<number>();
  const [locationId, setLocationId] = React.useState<number>();
  const [responsibleId, setResponsibleId] = React.useState<number>();
  const [period, setPeriod] = React.useState<[Dayjs, Dayjs] | null>(null);
  const [suppliers, setSuppliers] = React.useState<Supplier[]>([]);
  const [locations, setLocations] = React.useState<StorageLocation[]>([]);
  const [people, setPeople] = React.useState<User[]>([]);
  const [page, setPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(20);
  const [total, setTotal] = React.useState(0);

  React.useEffect(() => {
    void Promise.all([
      axiosInstance.get("/suppliers"),
      axiosInstance.get("/locations"),
      axiosInstance.get("/users"),
    ]).then(([s, l, u]) => {
      setSuppliers(s.data);
      setLocations(l.data);
      setPeople(u.data.filter((item: User) => item.role === "client" && item.is_active));
    });
  }, []);

  const load = React.useCallback(async () => {
    const params: Record<string, string | boolean | number> = {
      sort: "planned_date",
      order: "desc",
      limit: pageSize,
      offset: (page - 1) * pageSize,
    };
    if (archive) params.archive = true;
    if (search) params.search = search;
    if (status && !archive) params.status = status;
    if (supplierId) params.supplier_id = supplierId;
    if (locationId) params.location_id = locationId;
    if (responsibleId) params.responsible_id = responsibleId;
    if (period) {
      params.date_from = period[0].format("YYYY-MM-DD");
      params.date_to = period[1].format("YYYY-MM-DD");
    }
    const [list, sum] = await Promise.all([
      axiosInstance.get("/supplies", { params }),
      axiosInstance.get("/supplies/summary"),
    ]);
    setRows(list.data);
    setTotal(Number(list.headers["x-total-count"] ?? list.data.length));
    setSummary(sum.data);
  }, [archive, search, status, supplierId, locationId, responsibleId, period, page, pageSize]);

  React.useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <h1 className="page-title">{archive ? "Архив" : "Поставки"}</h1>
      <p className="page-lead">
        {archive
          ? "Завершённые и отменённые партии. Исходные записи не меняются."
          : "Сводка по шоуруму. Поиск по номеру и артикулу, фильтры по статусу, поставщику, месту, ответственному и периоду."}
      </p>
      {!archive ? (
        <div className="stat-grid">
          <div className="stat-card">
            <div className="stat-label">В пути</div>
            <div className="stat-value">{summary?.in_transit ?? 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">На проверке</div>
            <div className="stat-value">{summary?.on_check ?? 0}</div>
          </div>
          <div className={`stat-card ${summary?.overdue ? "danger" : ""}`}>
            <div className="stat-label">Просрочены</div>
            <div className="stat-value">{summary?.overdue ?? 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Завершены</div>
            <div className="stat-value">{summary?.completed ?? 0}</div>
          </div>
        </div>
      ) : null}
      <div className="toolbar">
        <Input.Search
          placeholder="Номер или артикул"
          allowClear
          onSearch={(value) => {
            setPage(1);
            setSearch(value);
          }}
          style={{ width: 260 }}
        />
        {archive ? null : (
          <Select
            allowClear
            placeholder="Статус"
            style={{ width: 180 }}
            options={STATUS_OPTIONS}
            onChange={(value) => {
              setPage(1);
              setStatus(value);
            }}
          />
        )}
        <Select
          allowClear
          placeholder="Поставщик"
          style={{ width: 180 }}
          options={suppliers.map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => {
            setPage(1);
            setSupplierId(value);
          }}
        />
        <Select
          allowClear
          placeholder="Место"
          style={{ width: 180 }}
          options={locations.map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => {
            setPage(1);
            setLocationId(value);
          }}
        />
        <Select
          allowClear
          placeholder="Ответственный"
          style={{ width: 200 }}
          options={people.map((item) => ({ value: item.id, label: item.full_name }))}
          onChange={(value) => {
            setPage(1);
            setResponsibleId(value);
          }}
        />
        <DatePicker.RangePicker
          onChange={(value) => {
            setPage(1);
            setPeriod(value as [Dayjs, Dayjs] | null);
          }}
        />
        {archive ? null : (
          <Link to="/supplies/create">
            <Button type="primary">Новая поставка</Button>
          </Link>
        )}
      </div>
      <Table
        rowKey="id"
        dataSource={rows}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (nextPage, nextSize) => {
            setPage(nextPage);
            setPageSize(nextSize);
          },
        }}
        onRow={(record) => ({ onClick: () => navigate(`/supplies/${record.id}`), className: "click-row" })}
        rowClassName={(record) => (record.is_overdue ? "overdue-row" : "")}
        columns={[
          { title: "Номер", dataIndex: "number" },
          { title: "Поставщик", dataIndex: "supplier_name" },
          { title: "Место", dataIndex: "location_name" },
          { title: "План", dataIndex: "planned_date" },
          {
            title: "Статус",
            render: (_: unknown, record: Supply) => (
              <StatusTag status={record.status} overdue={record.is_overdue} />
            ),
          },
          { title: "Ответственный", dataIndex: "responsible_name" },
          {
            title: "Состав",
            render: (_: unknown, record: Supply) =>
              record.items.map((item) => `${item.sku}×${item.planned_qty}`).join(", "),
          },
        ]}
      />
    </>
  );
};

export const ArchivePage: React.FC = () => <SupplyList archive />;
