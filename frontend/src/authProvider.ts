import type { AuthProvider } from "@refinedev/core";
import { axiosInstance } from "./dataProvider";

const homeByRole: Record<string, string> = {
  admin: "/users",
  client: "/supplies",
  validator: "/queue",
};

function persistSession(role: string, fullName: string, userId: number | string) {
  localStorage.setItem("role", role);
  localStorage.setItem("full_name", fullName);
  localStorage.setItem("user_id", String(userId));
  window.dispatchEvent(new Event("alllove-auth"));
}

export const authProvider: AuthProvider = {
  login: async ({ email, password }) => {
    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);
      const { data } = await axiosInstance.post("/auth/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      localStorage.setItem("token", data.access_token);

      const me = await axiosInstance.get("/auth/me");
      persistSession(me.data.role, me.data.full_name, me.data.id);
      return { success: true, redirectTo: homeByRole[me.data.role] ?? "/" };
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string }; status?: number } };
      const detail = err.response?.data?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : err.response
            ? "Неверный email или пароль"
            : "Сервер недоступен. Запустите backend и обновите страницу.";
      return { success: false, error: { name: "Ошибка входа", message } };
    }
  },

  logout: async () => {
    localStorage.clear();
    window.dispatchEvent(new Event("alllove-auth"));
    return { success: true, redirectTo: "/login" };
  },

  check: async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      return { authenticated: false, redirectTo: "/login" };
    }
    try {
      const me = await axiosInstance.get("/auth/me");
      persistSession(me.data.role, me.data.full_name, me.data.id);
      return { authenticated: true };
    } catch {
      localStorage.clear();
      window.dispatchEvent(new Event("alllove-auth"));
      return { authenticated: false, redirectTo: "/login" };
    }
  },

  getPermissions: async () => localStorage.getItem("role"),

  getIdentity: async () => ({
    id: Number(localStorage.getItem("user_id") || 0),
    name: localStorage.getItem("full_name") || "Пользователь",
  }),

  onError: async (error) => {
    if (error?.response?.status === 401) {
      return { logout: true, redirectTo: "/login" };
    }
    return { error };
  },
};
