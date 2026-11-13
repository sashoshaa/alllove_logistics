export type Role = "admin" | "validator" | "client";

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone?: string | null;
  role: Role;
  is_active: boolean;
}

export interface Supplier {
  id: number;
  name: string;
  contact?: string | null;
  address?: string | null;
  is_active: boolean;
}

export interface StorageLocation {
  id: number;
  name: string;
  address?: string | null;
  type: "warehouse" | "showroom";
  is_active: boolean;
}

export interface CatalogItem {
  id: number;
  sku: string;
  name: string;
  category?: string | null;
  size?: string | null;
  color?: string | null;
  is_active: boolean;
}

export interface SupplyItem {
  id: number;
  catalog_item_id: number;
  planned_qty: number;
  actual_qty?: number | null;
  sku?: string | null;
  name?: string | null;
  category?: string | null;
  size?: string | null;
  color?: string | null;
  difference?: number | null;
}

export interface DocumentFile {
  id: number;
  supply_id: number;
  original_name: string;
  content_type: string;
  size: number;
  uploaded_by_id: number;
  created_at: string;
}

export interface Supply {
  id: number;
  number: string;
  supplier_id: number;
  supplier_name?: string | null;
  location_id: number;
  location_name?: string | null;
  location_type?: string | null;
  planned_date: string;
  actual_date?: string | null;
  status: string;
  status_label?: string | null;
  responsible_id: number;
  responsible_name?: string | null;
  created_by_id: number;
  created_by_name?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
  overdue_days: number;
  items: SupplyItem[];
  documents: DocumentFile[];
}

export interface NotificationItem {
  id: number;
  type: string;
  title: string;
  message: string;
  supply_id?: number | null;
  is_read: boolean;
  created_at: string;
}
