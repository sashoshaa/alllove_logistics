from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Optional

import httpx

try:
    from desktop.api import ApiClient, ApiError
except ImportError:  # python desktop/app.py
    from api import ApiClient, ApiError

IVORY = "#F6F1EA"
PAPER = "#FFFCF8"
INK = "#1C1410"
MUTED = "#7A6A5E"
WINE = "#7A2E2A"
GOLD = "#C4A574"
LINE = "#E6D9CC"
OVERDUE = "#FBF3F1"
DEFAULT_API = os.environ.get("ALLLOVE_API_URL", "http://127.0.0.1:8001")
SETTINGS_PATH = Path.home() / ".alllove_desktop.json"


def load_settings() -> dict[str, str]:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_settings(values: dict[str, str]) -> None:
    SETTINGS_PATH.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")


def open_file(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


class ValidatorApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("AllLove — проверка поставок")
        self.root.minsize(720, 560)
        self.root.geometry("1100x720")
        self.root.configure(bg=IVORY)
        self.api = ApiClient(DEFAULT_API)
        self.queue: list[dict[str, Any]] = []
        self.current: Optional[dict[str, Any]] = None
        self.facts: dict[int, tk.StringVar] = {}
        self.item_rows: list[tk.Widget] = []
        self._build_styles()
        self._build_login()
        self._build_workspace()
        self.show_login()

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background=IVORY)
        style.configure("Paper.TFrame", background=PAPER)
        style.configure("TLabel", background=IVORY, foreground=INK, font=("Helvetica Neue", 13))
        style.configure("Muted.TLabel", background=IVORY, foreground=MUTED, font=("Helvetica Neue", 12))
        style.configure("Title.TLabel", background=IVORY, foreground=INK, font=("Georgia", 28))
        style.configure("Brand.TLabel", background=IVORY, foreground=WINE, font=("Georgia", 36))
        style.configure("Paper.TLabel", background=PAPER, foreground=INK, font=("Helvetica Neue", 13))
        style.configure("Head.TLabel", background=PAPER, foreground=INK, font=("Georgia", 22))
        style.configure("TEntry", fieldbackground=PAPER, foreground=INK)
        style.configure("Wine.TButton", background=WINE, foreground="#FFFCF8", font=("Helvetica Neue", 13, "bold"))
        style.map("Wine.TButton", background=[("active", "#5E2320")])
        style.configure("Ghost.TButton", background=PAPER, foreground=INK, font=("Helvetica Neue", 12))
        style.configure("Treeview", background=PAPER, fieldbackground=PAPER, foreground=INK, rowheight=28)
        style.configure("Treeview.Heading", background="#F3EBE3", foreground=MUTED, font=("Helvetica Neue", 11))
        style.map("Treeview", background=[("selected", WINE)], foreground=[("selected", "#FFFCF8")])

    def _build_login(self) -> None:
        self.login_frame = tk.Frame(self.root, bg=IVORY)
        card = tk.Frame(self.login_frame, bg=PAPER, padx=36, pady=32, highlightbackground=LINE, highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(card, text="AllLove", style="Brand.TLabel", background=PAPER).pack(anchor="w")
        ttk.Label(
            card,
            text="Рабочее место валидатора",
            style="Muted.TLabel",
            background=PAPER,
        ).pack(anchor="w", pady=(0, 18))
        ttk.Label(card, text="Email", style="Paper.TLabel").pack(anchor="w")
        self.email_var = tk.StringVar(value=load_settings().get("email", "validator@alllove.ru"))
        ttk.Entry(card, textvariable=self.email_var, width=36).pack(anchor="w", pady=(4, 12))
        ttk.Label(card, text="Пароль", style="Paper.TLabel").pack(anchor="w")
        self.password_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.password_var, show="•", width=36).pack(anchor="w", pady=(4, 12))
        ttk.Label(card, text="Адрес сервера", style="Paper.TLabel").pack(anchor="w")
        self.api_var = tk.StringVar(value=load_settings().get("api_url", DEFAULT_API))
        ttk.Entry(card, textvariable=self.api_var, width=36).pack(anchor="w", pady=(4, 18))
        ttk.Button(card, text="Войти", style="Wine.TButton", command=self.do_login).pack(anchor="w")
        self.login_status = ttk.Label(card, text="", style="Muted.TLabel", background=PAPER)
        self.login_status.pack(anchor="w", pady=(12, 0))
        self.root.bind("<Return>", lambda _event: self.do_login() if self.login_frame.winfo_ismapped() else None)

    def _build_workspace(self) -> None:
        self.work_frame = tk.Frame(self.root, bg=IVORY)
        header = tk.Frame(self.work_frame, bg=IVORY, padx=20, pady=16)
        header.pack(fill="x")
        ttk.Label(header, text="AllLove", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="  проверка поставок", style="Muted.TLabel").pack(side="left")
        ttk.Button(header, text="Выйти", style="Ghost.TButton", command=self.do_logout).pack(side="right")
        ttk.Button(header, text="Уведомления", style="Ghost.TButton", command=self.show_notifications).pack(
            side="right", padx=8
        )
        ttk.Button(header, text="Обновить", style="Ghost.TButton", command=self.refresh_queue).pack(side="right")
        self.user_label = ttk.Label(header, text="", style="Muted.TLabel")
        self.user_label.pack(side="right", padx=12)

        panes = tk.PanedWindow(self.work_frame, orient="horizontal", bg=IVORY, sashwidth=6)
        panes.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        left = tk.Frame(panes, bg=PAPER, highlightbackground=LINE, highlightthickness=1)
        ttk.Label(left, text="Очередь «На проверке»", style="Head.TLabel").pack(anchor="w", padx=16, pady=(16, 8))
        self.queue_list = tk.Listbox(
            left,
            activestyle="none",
            bg=PAPER,
            fg=INK,
            selectbackground=WINE,
            selectforeground="#FFFCF8",
            highlightthickness=0,
            borderwidth=0,
            font=("Helvetica Neue", 13),
        )
        self.queue_list.pack(fill="both", expand=True, padx=12, pady=(0, 16))
        self.queue_list.bind("<<ListboxSelect>>", self.on_select_supply)
        panes.add(left, minsize=260, width=300)

        right = tk.Frame(panes, bg=PAPER, highlightbackground=LINE, highlightthickness=1)
        self.detail_title = ttk.Label(right, text="Выберите поставку", style="Head.TLabel")
        self.detail_title.pack(anchor="w", padx=16, pady=(16, 4))
        self.detail_meta = ttk.Label(right, text="", style="Muted.TLabel", background=PAPER, wraplength=640)
        self.detail_meta.pack(anchor="w", padx=16, pady=(0, 8))
        self.docs_frame = tk.Frame(right, bg=PAPER)
        self.docs_frame.pack(fill="x", padx=16, pady=(0, 8))
        self.items_canvas = tk.Canvas(right, bg=PAPER, highlightthickness=0)
        scroll = ttk.Scrollbar(right, orient="vertical", command=self.items_canvas.yview)
        self.items_inner = tk.Frame(self.items_canvas, bg=PAPER)
        self.items_inner.bind(
            "<Configure>",
            lambda event: self.items_canvas.configure(scrollregion=self.items_canvas.bbox("all")),
        )
        self.items_canvas.create_window((0, 0), window=self.items_inner, anchor="nw")
        self.items_canvas.configure(yscrollcommand=scroll.set)
        self.items_canvas.pack(side="left", fill="both", expand=True, padx=(16, 0))
        scroll.pack(side="right", fill="y", pady=(0, 8))

        footer = tk.Frame(right, bg=PAPER, padx=16, pady=12)
        footer.pack(fill="x", side="bottom")
        ttk.Label(footer, text="Комментарий к результату", style="Paper.TLabel").pack(anchor="w")
        self.comment = tk.Text(footer, height=3, bg=IVORY, fg=INK, highlightthickness=1, highlightbackground=LINE, bd=0)
        self.comment.pack(fill="x", pady=(4, 10))
        actions = tk.Frame(footer, bg=PAPER)
        actions.pack(fill="x")
        ttk.Button(actions, text="Вернуть на уточнение", style="Ghost.TButton", command=self.return_back).pack(
            side="left"
        )
        self.submit_btn = ttk.Button(
            actions, text="Подтвердить проверку", style="Wine.TButton", command=self.submit_check
        )
        self.submit_btn.pack(side="right")
        panes.add(right, minsize=420)

    def show_login(self) -> None:
        self.work_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)
        self.password_var.set("")

    def show_workspace(self) -> None:
        self.login_frame.pack_forget()
        self.work_frame.pack(fill="both", expand=True)
        self.user_label.configure(text=self.api.full_name or "")
        self.refresh_queue()

    def do_login(self) -> None:
        email = self.email_var.get().strip()
        password = self.password_var.get()
        api_url = self.api_var.get().strip() or DEFAULT_API
        if not email or not password:
            self.login_status.configure(text="Введите email и пароль")
            return
        self.api = ApiClient(api_url)
        try:
            self.api.login(email, password)
        except ApiError as exc:
            self.login_status.configure(text=str(exc))
            return
        except httpx.HTTPError:
            self.login_status.configure(text="Сервер недоступен. Проверьте адрес и что backend запущен.")
            return
        save_settings({"email": email, "api_url": api_url})
        self.login_status.configure(text="")
        self.show_workspace()

    def do_logout(self) -> None:
        self.api.logout()
        self.queue = []
        self.current = None
        self.show_login()

    def refresh_queue(self) -> None:
        try:
            self.queue = self.api.queue()
        except ApiError as exc:
            messagebox.showerror("Очередь", str(exc), parent=self.root)
            return
        self.queue_list.delete(0, "end")
        for supply in self.queue:
            mark = " · просрочена" if supply.get("is_overdue") else ""
            self.queue_list.insert("end", f"{supply['number']}{mark}")
            if supply.get("is_overdue"):
                self.queue_list.itemconfig("end", bg=OVERDUE, fg=WINE)
        if self.queue:
            self.queue_list.selection_set(0)
            self.load_supply(self.queue[0]["id"])
        else:
            self.render_empty()

    def on_select_supply(self, _event: tk.Event | None = None) -> None:
        selection = self.queue_list.curselection()
        if not selection:
            return
        supply = self.queue[selection[0]]
        self.load_supply(supply["id"])

    def load_supply(self, supply_id: int) -> None:
        try:
            self.current = self.api.supply(supply_id)
        except ApiError as exc:
            messagebox.showerror("Поставка", str(exc), parent=self.root)
            return
        self.render_current()

    def render_empty(self) -> None:
        self.current = None
        self.detail_title.configure(text="Нет поставок в очереди")
        self.detail_meta.configure(text="Когда сотрудник шоурума отправит поставку на проверку, она появится здесь.")
        for child in self.docs_frame.winfo_children():
            child.destroy()
        self._clear_items()

    def render_current(self) -> None:
        supply = self.current
        if not supply:
            self.render_empty()
            return
        overdue = " · просрочена" if supply.get("is_overdue") else ""
        self.detail_title.configure(text=f"Проверка {supply['number']}{overdue}")
        self.detail_meta.configure(
            text=(
                f"{supply.get('supplier_name') or '—'} → {supply.get('location_name') or '—'}  ·  "
                f"план {supply.get('planned_date')}  ·  {supply.get('responsible_name') or '—'}"
            )
        )
        for child in self.docs_frame.winfo_children():
            child.destroy()
        documents = supply.get("documents") or []
        if not documents:
            ttk.Label(self.docs_frame, text="Документов нет", style="Muted.TLabel", background=PAPER).pack(anchor="w")
        for doc in documents:
            ttk.Button(
                self.docs_frame,
                text=doc["original_name"],
                style="Ghost.TButton",
                command=lambda item=doc: self.open_document(item),
            ).pack(anchor="w", pady=2)
        self._clear_items()
        header = tk.Frame(self.items_inner, bg="#F3EBE3")
        header.pack(fill="x", pady=(0, 6))
        for text, width in (("Артикул", 14), ("Наименование", 28), ("План", 8), ("Факт", 8), ("Разница", 14)):
            tk.Label(header, text=text, bg="#F3EBE3", fg=MUTED, font=("Helvetica Neue", 11), width=width, anchor="w").pack(
                side="left", padx=4, pady=6
            )
        self.facts = {}
        for item in supply.get("items") or []:
            row = tk.Frame(self.items_inner, bg=PAPER)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=item.get("sku") or "", bg=PAPER, width=14, anchor="w").pack(side="left", padx=4)
            tk.Label(row, text=item.get("name") or "", bg=PAPER, width=28, anchor="w").pack(side="left", padx=4)
            tk.Label(row, text=str(item.get("planned_qty") or 0), bg=PAPER, width=8, anchor="w").pack(side="left", padx=4)
            value = tk.StringVar(value="" if item.get("actual_qty") is None else str(item["actual_qty"]))
            self.facts[item["id"]] = value
            entry = ttk.Entry(row, textvariable=value, width=8)
            entry.pack(side="left", padx=4)
            diff = ttk.Label(row, text="", style="Paper.TLabel", width=14)
            diff.pack(side="left", padx=4)
            value.trace_add("write", lambda *_args, current=item, label=diff, var=value: self._update_diff(current, var, label))
            self._update_diff(item, value, diff)
            self.item_rows.append(row)
        self._update_submit_label()

    def _update_diff(self, item: dict[str, Any], var: tk.StringVar, label: ttk.Label) -> None:
        raw = var.get().strip()
        if raw == "":
            label.configure(text="")
            self._update_submit_label()
            return
        try:
            actual = int(raw)
        except ValueError:
            label.configure(text="число")
            self._update_submit_label()
            return
        delta = actual - int(item.get("planned_qty") or 0)
        if delta == 0:
            label.configure(text="совпало")
        elif delta > 0:
            label.configure(text=f"излишек {delta}")
        else:
            label.configure(text=f"недостача {abs(delta)}")
        self._update_submit_label()

    def _update_submit_label(self) -> None:
        if not self.current:
            self.submit_btn.configure(text="Подтвердить проверку")
            return
        values = []
        for item in self.current.get("items") or []:
            raw = self.facts.get(item["id"]).get().strip() if item["id"] in self.facts else ""
            if raw == "":
                self.submit_btn.configure(text="Заполните факт")
                return
            try:
                values.append(int(raw) != int(item.get("planned_qty") or 0))
            except ValueError:
                self.submit_btn.configure(text="Заполните факт")
                return
        self.submit_btn.configure(text="Зафиксировать расхождения" if any(values) else "Подтвердить проверку")

    def _clear_items(self) -> None:
        for widget in self.items_inner.winfo_children():
            widget.destroy()
        self.item_rows = []
        self.facts = {}

    def _collect_items(self) -> Optional[list[dict[str, Any]]]:
        if not self.current:
            return None
        rows = []
        for item in self.current.get("items") or []:
            raw = self.facts.get(item["id"]).get().strip() if item["id"] in self.facts else ""
            try:
                actual = int(raw)
            except ValueError:
                messagebox.showwarning("Проверка", "Укажите фактическое количество по каждой позиции.", parent=self.root)
                return None
            if actual < 0:
                messagebox.showwarning("Проверка", "Количество не может быть отрицательным.", parent=self.root)
                return None
            rows.append({"item_id": item["id"], "actual_qty": actual})
        if len(rows) != len(self.current.get("items") or []):
            messagebox.showwarning("Проверка", "Нужно заполнить фактическое количество по всем позициям.", parent=self.root)
            return None
        return rows

    def submit_check(self) -> None:
        self._send_check(return_back=False)

    def return_back(self) -> None:
        self._send_check(return_back=True)

    def _send_check(self, return_back: bool) -> None:
        if not self.current:
            return
        items = self._collect_items()
        if items is None:
            return
        try:
            self.api.check(
                self.current["id"],
                items,
                comment=self.comment.get("1.0", "end").strip(),
                return_for_clarification=return_back,
            )
        except ApiError as exc:
            messagebox.showerror("Проверка", str(exc), parent=self.root)
            return
        self.comment.delete("1.0", "end")
        messagebox.showinfo("Проверка", "Результат сохранён.", parent=self.root)
        self.refresh_queue()

    def open_document(self, doc: dict[str, Any]) -> None:
        suffix = Path(doc.get("original_name") or "document").suffix or ".bin"
        path = Path(tempfile.gettempdir()) / f"alllove-{doc['id']}{suffix}"
        try:
            self.api.download_document(doc["id"], path)
        except ApiError as exc:
            messagebox.showerror("Документ", str(exc), parent=self.root)
            return
        open_file(path)

    def show_notifications(self) -> None:
        try:
            notes = self.api.notifications()
        except ApiError as exc:
            messagebox.showerror("Уведомления", str(exc), parent=self.root)
            return
        window = tk.Toplevel(self.root)
        window.title("Уведомления")
        window.configure(bg=IVORY)
        window.geometry("420x480")
        if not notes:
            ttk.Label(window, text="Нет уведомлений", style="Muted.TLabel").pack(padx=20, pady=20)
            return
        canvas = tk.Canvas(window, bg=IVORY, highlightthickness=0)
        inner = tk.Frame(canvas, bg=IVORY)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.pack(fill="both", expand=True)
        inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        for note in notes:
            card = tk.Frame(inner, bg=PAPER, padx=12, pady=10, highlightbackground=LINE, highlightthickness=1)
            card.pack(fill="x", padx=16, pady=8)
            title = note.get("title") or "Уведомление"
            if not note.get("is_read"):
                title = "● " + title
            tk.Label(card, text=title, bg=PAPER, fg=INK, font=("Helvetica Neue", 13, "bold"), wraplength=360, justify="left").pack(
                anchor="w"
            )
            tk.Label(card, text=note.get("message") or "", bg=PAPER, fg=MUTED, wraplength=360, justify="left").pack(anchor="w")
            if not note.get("is_read"):
                ttk.Button(
                    card,
                    text="Прочитано",
                    style="Ghost.TButton",
                    command=lambda item=note, frame=card: self._read_note(item, frame),
                ).pack(anchor="e", pady=(6, 0))

    def _read_note(self, note: dict[str, Any], frame: tk.Frame) -> None:
        try:
            self.api.mark_read(note["id"])
        except ApiError as exc:
            messagebox.showerror("Уведомления", str(exc), parent=self.root)
            return
        for child in frame.winfo_children():
            if isinstance(child, ttk.Button):
                child.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    ValidatorApp().run()


if __name__ == "__main__":
    main()
