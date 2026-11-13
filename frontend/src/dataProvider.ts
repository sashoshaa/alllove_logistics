import axios from "axios";
import type { DataProvider } from "@refinedev/core";

const API_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "/api" : "http://127.0.0.1:8000");

const axiosInstance = axios.create({ baseURL: API_URL });

axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const resourcePath: Record<string, string> = {
  users: "/users",
  suppliers: "/suppliers",
  locations: "/locations",
  catalog: "/catalog",
  supplies: "/supplies",
  audit: "/admin/audit",
};

export const dataProvider: DataProvider = {
  getList: async ({ resource, meta }) => {
    const path = resourcePath[resource] ?? `/${resource}`;
    const params = { ...(meta?.query ?? {}) };
    if (resource === "suppliers" || resource === "locations" || resource === "catalog") {
      params.include_inactive = true;
    }
    const { data } = await axiosInstance.get(path, { params });
    return { data, total: data.length };
  },
  getOne: async ({ resource, id }) => {
    const path = resourcePath[resource] ?? `/${resource}`;
    const { data } = await axiosInstance.get(`${path}/${id}`);
    return { data };
  },
  create: async ({ resource, variables }) => {
    const path = resourcePath[resource] ?? `/${resource}`;
    const { data } = await axiosInstance.post(path, variables);
    return { data };
  },
  update: async ({ resource, id, variables }) => {
    const path = resourcePath[resource] ?? `/${resource}`;
    const { data } = await axiosInstance.patch(`${path}/${id}`, variables);
    return { data };
  },
  deleteOne: async ({ resource, id }) => {
    const path = resourcePath[resource] ?? `/${resource}`;
    await axiosInstance.delete(`${path}/${id}`);
    return { data: { id } as never };
  },
  getApiUrl: () => API_URL,
};

export { axiosInstance, API_URL };
