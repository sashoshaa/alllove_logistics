export const STATUS_OPTIONS = [
  { value: "created", label: "Создана" },
  { value: "in_transit", label: "В пути" },
  { value: "on_check", label: "На проверке" },
  { value: "has_discrepancies", label: "Есть расхождения" },
  { value: "checked", label: "Проверена" },
  { value: "completed", label: "Завершена" },
  { value: "cancelled", label: "Отменена" },
];

export const ROLE_LABELS: Record<string, string> = {
  admin: "Администратор",
  validator: "Валидатор",
  client: "Сотрудник шоурума",
};

export const STATUS_COLORS: Record<string, string> = {
  created: "default",
  in_transit: "geekblue",
  on_check: "gold",
  has_discrepancies: "red",
  checked: "green",
  completed: "success",
  cancelled: "default",
};
