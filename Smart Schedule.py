# 作者: 诗弦绸覆
# 协议: CC BY-NC-SA 4.0 (禁止未经授权的商业使用)

import tkinter as tk
from tkinter import ttk, font, simpledialog, messagebox
import json
import os
import sys
import ctypes
from datetime import datetime, timedelta
import copy

# ==================== 单实例检测 ====================
def is_single_instance():
    try:
        mutex_name = "SmartTodoApp_Mutex_2026_Final"
        mutex = ctypes.windll.kernel32.CreateMutexW(None, True, mutex_name)
        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == 183:
            return False
        return True
    except:
        return True

if not is_single_instance():
    sys.exit(0)

# ==================== 日历计算类 ====================
class CalendarCalculator:
    @staticmethod
    def get_days_in_month(year, month):
        if month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif month in [4, 6, 9, 11]:
            return 30
        elif month == 2:
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                return 29
            else:
                return 28
    
    @staticmethod
    def get_first_weekday(year, month):
        return datetime(year, month, 1).weekday()

# ==================== 日历弹窗组件 ====================
class CalendarPopup:
    def __init__(self, parent, app_instance):
        self.parent = parent
        self.app = app_instance
        self.current_date = datetime.strptime(app_instance.current_date, "%Y-%m-%d")
        self.year = self.current_date.year
        self.month = self.current_date.month
        self.calendar_buttons = []
        
        self.top = tk.Toplevel(parent)
        self.top.title("📅 日历查询")
        self.top.geometry("520x680")
        self.top.resizable(False, False)
        self.top.attributes('-topmost', True)
        self.top.transient(parent)
        self.top.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.top.update_idletasks()
        self.top.lift()
        self.top.focus_force()
        
        self.setup_ui()
        self.render_calendar()

    def on_close(self):
        for btn in self.calendar_buttons:
            try:
                btn.destroy()
            except:
                pass
        self.calendar_buttons.clear()
        self.top.destroy()

    def setup_ui(self):
        header_frame = ttk.Frame(self.top, padding="10")
        header_frame.pack(fill=tk.X)
        
        btn_prev = ttk.Button(header_frame, text="◀ 上月", width=6, command=self.prev_month)
        btn_prev.pack(side=tk.LEFT, padx=5)
        
        self.lbl_month = ttk.Label(header_frame, text="", font=("Microsoft YaHei", 16, "bold"))
        self.lbl_month.pack(side=tk.LEFT, expand=True)
        
        btn_next = ttk.Button(header_frame, text="下月 ▶", width=6, command=self.next_month)
        btn_next.pack(side=tk.RIGHT, padx=5)
        
        btn_today = ttk.Button(header_frame, text="今天", width=4, command=self.jump_to_real_today)
        btn_today.pack(side=tk.RIGHT, padx=5)

        week_frame = ttk.Frame(self.top)
        week_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        weeks = ["一", "二", "三", "四", "五", "六", "日"]
        for i, w in enumerate(weeks):
            lbl = ttk.Label(week_frame, text=w, font=("Microsoft YaHei", 11, "bold"), 
                          anchor="center", foreground="#666666", width=5)
            lbl.pack(side=tk.LEFT, expand=True)

        self.canvas = tk.Canvas(self.top, width=490, height=420, bg="#ffffff", highlightthickness=1, highlightbackground="#dddddd")
        self.canvas.pack(padx=15, pady=5)
        
        self.detail_frame = ttk.LabelFrame(self.top, text="当日概况", padding="8")
        self.detail_frame.pack(fill=tk.X, padx=15, pady=(10, 15))
        self.lbl_detail = ttk.Label(self.detail_frame, text="点击日期查看详情", 
                                   font=("Microsoft YaHei", 9), foreground="#888888")
        self.lbl_detail.pack()

    def prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self.update_header()
        self.render_calendar()

    def next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self.update_header()
        self.render_calendar()
        
    def jump_to_real_today(self):
        now = datetime.now()
        self.year = now.year
        self.month = now.month
        self.update_header()
        self.render_calendar()

    def update_header(self):
        self.lbl_month.config(text=f"{self.year}年 {self.month}月")

    def get_day_status(self, day):
        """
        状态定义:
        0: 无任务或未开始
        1: 有重要任务未完成 (红色)
        2: 重要任务已完成 AND 用户已点击"完成今天" (绿色 - 计入统计)
        3: 重要任务已完成 BUT 用户未点击"完成今天" (黄色 - 待确认)
        4: 有任务但无重要任务，且未点击完成 (普通进行中)
        """
        date_str = f"{self.year}-{self.month:02d}-{day:02d}"
        if date_str not in self.app.data:
            return 0
        
        day_data = self.app.data[date_str]
        slots = day_data.get("slots", [])
        is_day_completed_flag = day_data.get("day_completed", False)
        
        total_tasks = 0
        has_pending_imp = False
        has_any_task = False
        
        for slot in slots:
            for task in slot.get("tasks", []):
                total_tasks += 1
                has_any_task = True
                if task.get("important"):
                    if not task.get("done"):
                        has_pending_imp = True
        
        if not has_any_task:
            return 0
            
        if has_pending_imp:
            return 1  # 红色：重要任务卡住
        
        # 重要任务都做完了
        if is_day_completed_flag:
            return 2  # 绿色：已归档
        else:
            return 3  # 黄色：重要任务完成，等待确认

    def get_day_detail(self, day):
        date_str = f"{self.year}-{self.month:02d}-{day:02d}"
        if date_str not in self.app.data:
            return "无任务记录"
        
        day_data = self.app.data[date_str]
        slots = day_data.get("slots", [])
        total = done = imp_total = imp_done = 0
        for slot in slots:
            for task in slot.get("tasks", []):
                total += 1
                if task.get("done"): done += 1
                if task.get("important"):
                    imp_total += 1
                    if task.get("done"): imp_done += 1
        
        status = "未确认"
        if day_data.get("day_completed", False):
            status = "已归档"
        elif imp_total > 0 and imp_done == imp_total:
            status = "待确认"
            
        if total == 0: return "无任务记录"
        return f"总：{total} | 重要：{imp_done}/{imp_total} | {status}"

    def render_calendar(self):
        self.canvas.delete("all")
        for btn in self.calendar_buttons:
            try:
                btn.destroy()
            except:
                pass
        self.calendar_buttons.clear()
        
        num_days = CalendarCalculator.get_days_in_month(self.year, self.month)
        first_weekday = CalendarCalculator.get_first_weekday(self.year, self.month)
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        cell_width = 70
        cell_height = 60
        start_x = 15
        start_y = 10
        
        for row in range(6):
            for col in range(7):
                x1 = start_x + col * cell_width
                y1 = start_y + row * cell_height
                x2 = x1 + cell_width
                y2 = y1 + cell_height
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="#eeeeee", fill="#ffffff")
        
        cell_index = 0
        for row in range(6):
            for col in range(7):
                day = cell_index - first_weekday + 1
                
                x = start_x + col * cell_width + 5
                y = start_y + row * cell_height + 5
                
                if 1 <= day <= num_days:
                    date_str = f"{self.year}-{self.month:02d}-{day:02d}"
                    status = self.get_day_status(day)
                    
                    fg_color = "#000000"
                    bg_color = "#ffffff"
                    status_icon = ""
                    font_weight = "normal"
                    
                    if date_str == self.app.current_date:
                        bg_color = "#e8f4fd"
                        fg_color = "#0066cc"
                        font_weight = "bold"
                    
                    # 状态映射
                    if status == 1: # 重要未完成
                        fg_color = "#d9534f"
                        status_icon = "🔴"
                    elif status == 2: # 已归档 (绿色)
                        fg_color = "#28a745"
                        status_icon = "🟢"
                    elif status == 3: # 待确认 (黄色)
                        fg_color = "#f0ad4e"
                        status_icon = "🟡"
                    elif status == 4: # 普通进行中
                        fg_color = "#5bc0de"
                        status_icon = "🔵"
                    elif date_str == today_str:
                        fg_color = "#007bff"
                        status_icon = "📍"
                    
                    btn_text = f"{status_icon}\n{day}" if status_icon else str(day)
                    
                    btn = tk.Button(
                        self.canvas,
                        text=btn_text,
                        width=8,
                        height=2,
                        relief=tk.RAISED,
                        bg=bg_color,
                        fg=fg_color,
                        font=("Microsoft YaHei", 10, font_weight),
                        command=lambda d=day: self.on_date_click(d)
                    )
                    
                    btn_window = self.canvas.create_window(x + 30, y + 25, window=btn, anchor="center")
                    self.calendar_buttons.append(btn)
                    
                    btn.bind("<Enter>", lambda e, b=btn, d=day: self.on_hover(b, d))
                    btn.bind("<Leave>", lambda e, b=btn: self.on_leave(b))
                
                cell_index += 1
        
        self.canvas.update_idletasks()
        self.top.update_idletasks()

    def on_hover(self, btn, day):
        btn.config(relief=tk.SUNKEN)
        detail = self.get_day_detail(day)
        self.lbl_detail.config(text=f"{self.year}-{self.month:02d}-{day:02d}  {detail}")

    def on_leave(self, btn):
        btn.config(relief=tk.RAISED)

    def on_date_click(self, day):
        new_date_str = f"{self.year}-{self.month:02d}-{day:02d}"
        self.app.current_date = new_date_str
        if new_date_str not in self.app.data:
            self.app.data[new_date_str] = {"slots": [{"name": "上午", "tasks": []}, {"name": "下午", "tasks": []}], "checked_in": False, "day_completed": False}
        self.app.refresh_ui()
        self.app.save_data()
        self.on_close()


# ==================== 主程序 ====================
class SmartTodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能日程管理")
        self.root.geometry("550x700")
        self.root.minsize(500, 600)
        
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.root.bind("<Escape>", lambda e: self.hide_window())
        self.root.attributes('-topmost', True)

        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.data_file = "smart_tasks.json"
        self.data = self.load_data()
        
        if self.current_date not in self.data:
            self.data[self.current_date] = {
                "slots": [{"name": "上午", "tasks": []}, {"name": "下午", "tasks": []}],
                "checked_in": False,
                "day_completed": False
            }
            self.save_data()

        self.weekly_plan_editing = False
        self.month_rows = {}
        self.weekly_plan_label = None
        self.weekly_plan_entry = None

        self.setup_styles()
        self.create_widgets()
        self.refresh_ui()
        
        self.calendar_popup = None

    def setup_styles(self):
        self.style = ttk.Style()
        if 'clam' in self.style.theme_names():
            self.style.theme_use('clam')
        self.style.configure("Normal.TCheckbutton", font=("Microsoft YaHei", 11), foreground="#000000")
        self.style.configure("Done.TCheckbutton", font=("Microsoft YaHei", 11), foreground="#888888")
        self.title_font = font.Font(family="Microsoft YaHei", size=14, weight="bold")

    def create_widgets(self):
        # === 导航栏 ===
        nav_frame = ttk.Frame(self.root, padding="8")
        nav_frame.pack(fill=tk.X)
        
        self.btn_prev = ttk.Button(nav_frame, text="<", width=3, command=self.change_date(-1))
        self.btn_prev.pack(side=tk.LEFT)
        
        self.lbl_date = ttk.Label(nav_frame, text="", font=self.title_font, cursor="hand2")
        self.lbl_date.pack(side=tk.LEFT, expand=True)
        self.lbl_date.bind("<Button-1>", lambda e: self.jump_to_today())
        
        self.btn_next = ttk.Button(nav_frame, text=">", width=3, command=self.change_date(1))
        self.btn_next.pack(side=tk.RIGHT)
        
        self.btn_calendar = ttk.Button(nav_frame, text="📅", width=3, command=self.open_calendar)
        self.btn_calendar.pack(side=tk.RIGHT, padx=2)

        # === 全年统计表格 ===
        self.year_table_frame = ttk.LabelFrame(self.root, text="📊 月度对比 (仅统计已确认完成的天数)", padding="5")
        self.year_table_frame.pack(fill=tk.X, padx=10, pady=3)
        
        header_frame = ttk.Frame(self.year_table_frame)
        header_frame.pack(fill=tk.X, pady=(0, 3))
        
        ttk.Label(header_frame, text="月", font=("Microsoft YaHei", 9, "bold"), width=4, anchor="center").pack(side=tk.LEFT, padx=3)
        ttk.Label(header_frame, text="打卡", font=("Microsoft YaHei", 9, "bold"), width=6, anchor="center", foreground="#0066cc").pack(side=tk.LEFT, padx=3)
        ttk.Label(header_frame, text="完成", font=("Microsoft YaHei", 9, "bold"), width=6, anchor="center", foreground="#28a745").pack(side=tk.LEFT, padx=3)
        
        for month in range(1, 13):
            row_frame = ttk.Frame(self.year_table_frame)
            row_frame.pack(fill=tk.X, pady=0)
            
            lbl_month = ttk.Label(row_frame, text=f"{month}", font=("Microsoft YaHei", 9), width=4, anchor="center")
            lbl_month.pack(side=tk.LEFT, padx=3)
            
            lbl_checkin = ttk.Label(row_frame, text="-", font=("Microsoft YaHei", 9), width=6, anchor="center", foreground="#0066cc")
            lbl_checkin.pack(side=tk.LEFT, padx=3)
            
            lbl_done = ttk.Label(row_frame, text="-", font=("Microsoft YaHei", 9), width=6, anchor="center", foreground="#28a745")
            lbl_done.pack(side=tk.LEFT, padx=3)
            
            self.month_rows[month] = {
                "checkin": lbl_checkin,
                "done": lbl_done,
                "frame": row_frame
            }

        # === 每周计划区域 ===
        self.weekly_plan_frame = ttk.LabelFrame(self.root, text="📋 每周计划", padding="8")
        self.weekly_plan_frame.pack(fill=tk.X, padx=10, pady=3)
        
        self.weekly_plan_label = tk.Label(
            self.weekly_plan_frame, 
            text="", 
            font=("Microsoft YaHei", 10),
            fg="#333333",
            bg="#f0f0f0",
            anchor="w",
            cursor="hand2",
            justify=tk.LEFT
        )
        self.weekly_plan_label.pack(fill=tk.X, expand=True)
        self.weekly_plan_label.bind("<Double-Button-1>", lambda e: self.enable_weekly_plan_edit())
        
        self.weekly_plan_entry = tk.Text(
            self.weekly_plan_frame,
            height=4,
            width=50,
            font=("Microsoft YaHei", 10),
            bg="#ffffff",
            fg="#333333",
            relief=tk.SUNKEN,
            borderwidth=1,
            wrap=tk.WORD
        )
        self.weekly_plan_entry.bind("<FocusOut>", lambda e: self.disable_weekly_plan_edit())
        self.weekly_plan_entry.bind("<Control-Return>", lambda e: self.disable_weekly_plan_edit())
        self.weekly_plan_entry.pack_forget()

        # === 任务延续区域 ===
        self.continue_frame = ttk.Frame(self.root, padding="5")
        self.continue_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.lbl_continue_tip = ttk.Label(self.continue_frame, text="", 
                                         font=("Microsoft YaHei", 9), foreground="#666666")
        self.lbl_continue_tip.pack(side=tk.LEFT, expand=True)
        
        self.btn_continue_yesterday = ttk.Button(self.continue_frame, text="📋 延续昨天任务", 
                                                  width=12, command=self.continue_yesterday_tasks)
        self.btn_continue_yesterday.pack(side=tk.RIGHT, padx=2)
        
        self.btn_new_day = ttk.Button(self.continue_frame, text="🆕 新建今天任务", 
                                       width=12, command=self.new_day_tasks)
        self.btn_new_day.pack(side=tk.RIGHT, padx=2)

        # === 当日打卡状态 ===
        self.checkin_frame = ttk.Frame(self.root, padding="5")
        self.checkin_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.lbl_checkin_status = ttk.Label(self.checkin_frame, text="", 
                                           font=("Microsoft YaHei", 10, "bold"))
        self.lbl_checkin_status.pack(side=tk.LEFT)
        
        self.btn_checkin = ttk.Button(self.checkin_frame, text="✅ 打卡", width=8,
                                      command=self.do_checkin)
        self.btn_checkin.pack(side=tk.RIGHT)

        # === 任务内容区域 ===
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg="#f9f9f9")
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.content_frame = ttk.Frame(self.canvas)

        self.content_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # === 操作栏 ===
        action_frame = ttk.Frame(self.root, padding="8")
        action_frame.pack(fill=tk.X)
        
        btn_add_slot = ttk.Button(action_frame, text="+ 添加时段", command=self.add_new_slot)
        btn_add_slot.pack(side=tk.LEFT)
        
        self.btn_finish_day = ttk.Button(action_frame, text="✅ 完成今天", command=self.finish_day)
        self.btn_finish_day.pack(side=tk.RIGHT)

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    def get_current_slots(self):
        return self.data.setdefault(self.current_date, {"slots": [], "day_completed": False}).setdefault("slots", [])
    
    def check_important_tasks_status(self, date_str):
        """
        检查重要任务状态
        返回: (has_important_tasks, all_important_done)
        """
        if date_str not in self.data:
            return False, True
            
        slots = self.data[date_str].get("slots", [])
        has_important = False
        all_done = True
        
        for slot in slots:
            for task in slot.get("tasks", []):
                if task.get("important"):
                    has_important = True
                    if not task.get("done"):
                        all_done = False
        
        return has_important, all_done

    def get_yesterday_date(self):
        curr = datetime.strptime(self.current_date, "%Y-%m-%d")
        yesterday = curr - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")

    def has_yesterday_tasks(self):
        yesterday = self.get_yesterday_date()
        if yesterday not in self.data:
            return False
        slots = self.data[yesterday].get("slots", [])
        for slot in slots:
            if slot.get("tasks", []):
                return True
        return False

    # 【核心修改】统计逻辑：只看 day_completed 标记
    def get_month_stats(self, year, month):
        checkin_count = 0
        completed_days = 0
        num_days = CalendarCalculator.get_days_in_month(year, month)
        for d in range(1, num_days + 1):
            date_str = f"{year}-{month:02d}-{d:02d}"
            if date_str in self.data:
                day_data = self.data[date_str]
                if day_data.get("checked_in", False):
                    checkin_count += 1
                # 只有当用户手动点击了"完成今天"，这里才计为 1
                if day_data.get("day_completed", False):
                    completed_days += 1
        return checkin_count, completed_days

    def get_year_stats(self, year):
        year_data = {}
        for month in range(1, 13):
            checkin, completed = self.get_month_stats(year, month)
            year_data[month] = {"checkin": checkin, "completed": completed}
        return year_data

    def do_checkin(self):
        date_data = self.data.setdefault(self.current_date, {"slots": [], "checked_in": False, "day_completed": False})
        if date_data.get("checked_in", False):
            messagebox.showinfo("提示", "✅ 今日已打卡！")
            return
        
        date_data["checked_in"] = True
        date_data["checkin_time"] = datetime.now().strftime("%H:%M")
        self.save_data()
        self.refresh_ui()
        messagebox.showinfo("打卡成功", "🎉 打卡成功！继续加油！")

    def open_calendar(self):
        if self.calendar_popup and self.calendar_popup.top.winfo_exists():
            self.calendar_popup.top.lift()
            self.calendar_popup.top.focus_force()
            return
        self.calendar_popup = CalendarPopup(self.root, self)

    def enable_weekly_plan_edit(self):
        if self.weekly_plan_editing:
            return
        self.weekly_plan_editing = True
        self.weekly_plan_label.pack_forget()
        self.weekly_plan_entry.pack(fill=tk.X, expand=True)
        current_plan = self.data.get("weekly_plan", "")
        self.weekly_plan_entry.delete("1.0", "end")
        self.weekly_plan_entry.insert("1.0", current_plan)
        self.weekly_plan_entry.focus_set()
        self.weekly_plan_entry.tag_add("sel", "1.0", "end")

    def disable_weekly_plan_edit(self, event=None):
        if not self.weekly_plan_editing:
            return
        self.weekly_plan_editing = False
        plan_text = self.weekly_plan_entry.get("1.0", "end-1c").strip()
        self.data["weekly_plan"] = plan_text
        self.save_data()
        self.weekly_plan_entry.pack_forget()
        self.weekly_plan_label.pack(fill=tk.X, expand=True)
        if plan_text:
            self.weekly_plan_label.config(text=plan_text)
        else:
            self.weekly_plan_label.config(text="📝 双击此处设置每周计划（如：每周五更新视频、每周六更新小说）")

    def continue_yesterday_tasks(self):
        yesterday = self.get_yesterday_date()
        if yesterday not in self.data:
            messagebox.showinfo("提示", "❌ 昨天没有任务记录，无法延续！")
            return
        yesterday_slots = self.data[yesterday].get("slots", [])
        if not yesterday_slots:
            messagebox.showinfo("提示", "❌ 昨天没有任务记录，无法延续！")
            return
        
        total_tasks = 0
        undone_tasks = 0
        for slot in yesterday_slots:
            for task in slot.get("tasks", []):
                total_tasks += 1
                if not task.get("done", False):
                    undone_tasks += 1
        
        choice = messagebox.askyesnocancel(
            "延续任务",
            f"📋 昨天共有 {total_tasks} 个任务，其中 {undone_tasks} 个未完成\n\n"
            f"选择延续方式：\n"
            f"✅ 是 - 只延续未完成的任务\n"
            f"❌ 否 - 延续所有任务\n"
            f"取消 - 不延续"
        )
        
        if choice is None:
            return
        
        if choice:
            new_slots = []
            for slot in yesterday_slots:
                new_slot = {"name": slot["name"], "tasks": []}
                for task in slot.get("tasks", []):
                    if not task.get("done", False):
                        new_task = copy.deepcopy(task)
                        new_task["done"] = False
                        new_slot["tasks"].append(new_task)
                if new_slot["tasks"]:
                    new_slots.append(new_slot)
        else:
            new_slots = copy.deepcopy(yesterday_slots)
            for slot in new_slots:
                for task in slot.get("tasks", []):
                    task["done"] = False
        
        if not new_slots:
            messagebox.showinfo("提示", "✅ 昨天所有任务已完成，无需延续！")
            return
        
        self.data[self.current_date]["slots"] = new_slots
        # 延续过来的新的一天，默认未完成
        self.data[self.current_date]["day_completed"] = False
        self.save_data()
        self.refresh_ui()
        messagebox.showinfo("成功", f"🎉 已延续 {sum(len(s['tasks']) for s in new_slots)} 个任务到今天！")

    def new_day_tasks(self):
        current_slots = self.get_current_slots()
        total_tasks = sum(len(s.get("tasks", [])) for s in current_slots)
        
        if total_tasks > 0:
            confirm = messagebox.askyesno(
                "确认清空",
                f"⚠️ 今天已有 {total_tasks} 个任务，清空后将无法恢复！\n\n确定要新建任务吗？"
            )
            if not confirm:
                return
        
        self.data[self.current_date]["slots"] = [
            {"name": "上午", "tasks": []},
            {"name": "下午", "tasks": []}
        ]
        self.data[self.current_date]["day_completed"] = False
        self.save_data()
        self.refresh_ui()
        messagebox.showinfo("成功", "🆕 已清空今天任务，可以重新制定计划！")

    def move_slot_up(self, slot_idx):
        slots = self.get_current_slots()
        if slot_idx > 0:
            slots[slot_idx], slots[slot_idx - 1] = slots[slot_idx - 1], slots[slot_idx]
            self.save_data()
            self.refresh_ui()

    def move_slot_down(self, slot_idx):
        slots = self.get_current_slots()
        if slot_idx < len(slots) - 1:
            slots[slot_idx], slots[slot_idx + 1] = slots[slot_idx + 1], slots[slot_idx]
            self.save_data()
            self.refresh_ui()

    def refresh_ui(self):
        date_obj = datetime.strptime(self.current_date, "%Y-%m-%d")
        self.lbl_date.config(text=date_obj.strftime("%Y年%m月%d日 %A"))
        
        year_data = self.get_year_stats(date_obj.year)
        for month in range(1, 13):
            data = year_data[month]
            row = self.month_rows[month]
            row["checkin"].config(text=str(data['checkin']) if data['checkin'] > 0 else "-")
            row["done"].config(text=str(data['completed']) if data['completed'] > 0 else "-")
            
            if month == date_obj.month:
                row["frame"].config(relief=tk.RIDGE, borderwidth=1)
            else:
                row["frame"].config(relief=tk.FLAT, borderwidth=0)

        if not self.weekly_plan_editing and self.weekly_plan_label:
            plan_text = self.data.get("weekly_plan", "")
            if plan_text:
                self.weekly_plan_label.config(text=plan_text)
            else:
                self.weekly_plan_label.config(text="📝 双击此处设置每周计划（如：每周五更新视频、每周六更新小说）")

        yesterday = self.get_yesterday_date()
        has_yesterday = self.has_yesterday_tasks()
        current_slots = self.get_current_slots()
        has_today_tasks = any(len(s.get("tasks", [])) > 0 for s in current_slots)
        
        if has_yesterday and not has_today_tasks:
            self.lbl_continue_tip.config(text="💡 昨天有任务记录，可以延续到今天", foreground="#0066cc")
            self.btn_continue_yesterday.config(state=tk.NORMAL)
        elif has_yesterday and has_today_tasks:
            self.lbl_continue_tip.config(text="✅ 今天已有任务，可选择延续或新建", foreground="#28a745")
            self.btn_continue_yesterday.config(state=tk.NORMAL)
        else:
            self.lbl_continue_tip.config(text="ℹ️ 昨天无任务记录", foreground="#888888")
            self.btn_continue_yesterday.config(state=tk.DISABLED)

        # === 状态栏逻辑 (基于重要任务 + 手动确认) ===
        date_data = self.data.get(self.current_date, {})
        is_checked_in = date_data.get("checked_in", False)
        is_day_completed_flag = date_data.get("day_completed", False)
        
        has_imp, all_imp_done = self.check_important_tasks_status(self.current_date)
        total_tasks_count = sum(len(s.get("tasks", [])) for s in current_slots)
        
        if is_checked_in:
            checkin_time = date_data.get("checkin_time", "?")
            status_text = f"✅ 已打卡 ({checkin_time})"
            self.lbl_checkin_status.config(text=status_text, foreground="#28a745")
            self.btn_checkin.config(text="✓ 已打卡", state=tk.DISABLED)
        else:
            self.lbl_checkin_status.config(text="⏰ 未打卡", foreground="#d9534f")
            self.btn_checkin.config(text="✅ 打卡", state=tk.NORMAL)
        
        # 按钮和状态后缀逻辑
        if total_tasks_count == 0:
            status_suffix = " | ⚪ 暂无任务"
            self.btn_finish_day.config(text="⚪ 请先添加任务", state=tk.DISABLED)
        elif not all_imp_done:
            # 有重要任务未完成
            status_suffix = " | 🔴 有待办重要任务"
            self.btn_finish_day.config(text="⚠️ 先完成重要任务", state=tk.DISABLED)
        elif is_day_completed_flag:
            # 重要任务完成 + 已点击确认
            status_suffix = " | 🟢 今日已归档"
            self.btn_finish_day.config(text="✓ 已完成", state=tk.DISABLED)
        else:
            # 重要任务完成 + 未点击确认
            status_suffix = " | 🟡 重要任务已完成，请确认"
            self.btn_finish_day.config(text="✅ 确认完成今天", state=tk.NORMAL)
        
        base_text = self.lbl_checkin_status.cget('text').split(" | ")[0]
        self.lbl_checkin_status.config(text=f"{base_text}{status_suffix}")

        # === 渲染任务区域 ===
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        slots = self.get_current_slots()
        if not slots:
            ttk.Label(self.content_frame, text="暂无时段，请点击下方'+ 添加时段'", font=("Microsoft YaHei", 10), foreground="#999").pack(pady=20)
            return

        for s_idx, slot in enumerate(slots):
            slot_container = tk.Frame(self.content_frame, bg="#f0f0f0")
            slot_container.pack(fill=tk.X, pady=2)
            slot_container.config(relief=tk.RAISED, borderwidth=1)

            slot_header = tk.Frame(slot_container, bg="#f0f0f0")
            slot_header.pack(fill=tk.X, padx=5, pady=(8, 2))
            
            btn_up = ttk.Button(slot_header, text="↑", width=2, 
                               command=lambda idx=s_idx: self.move_slot_up(idx))
            btn_up.pack(side=tk.LEFT, padx=(5, 2))
            if s_idx == 0:
                btn_up.config(state=tk.DISABLED)
            
            btn_down = ttk.Button(slot_header, text="↓", width=2, 
                                 command=lambda idx=s_idx: self.move_slot_down(idx))
            btn_down.pack(side=tk.LEFT, padx=2)
            if s_idx == len(slots) - 1:
                btn_down.config(state=tk.DISABLED)
            
            lbl_name = tk.Label(slot_header, text=slot["name"], 
                               font=("Microsoft YaHei", 11, "bold"),
                               fg="#d9534f", bg="#f0f0f0")
            lbl_name.pack(side=tk.LEFT, padx=10)
            lbl_name.bind("<Double-Button-1>", lambda e, idx=s_idx: self.edit_slot_name(idx))
            
            btn_del_slot = ttk.Button(slot_header, text="×", width=2, command=lambda idx=s_idx: self.delete_slot(idx))
            btn_del_slot.pack(side=tk.RIGHT)
            
            tasks = slot.get("tasks", [])
            for t_idx, task in enumerate(tasks):
                row_frame = tk.Frame(slot_container, bg="#f0f0f0")
                row_frame.pack(fill=tk.X, padx=10, pady=1)
                
                is_done = task.get("done", False)
                is_imp = task.get("important", False)
                
                style_name = "Done.TCheckbutton" if is_done else "Normal.TCheckbutton"
                prefix = "⭐ " if is_imp else ""
                
                cb = ttk.Checkbutton(row_frame, text=f"{prefix}{task['text']}", style=style_name, 
                                    command=lambda s=s_idx, t=t_idx: self.toggle_task(s, t))
                cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
                cb.bind("<Double-Button-1>", lambda e, s=s_idx, t=t_idx: self.edit_task(s, t))
                row_frame.bind("<Double-Button-1>", lambda e, s=s_idx, t=t_idx: self.edit_task(s, t))
                
                btn_del = ttk.Button(row_frame, text="×", width=2, command=lambda s=s_idx, t=t_idx: self.delete_task(s, t))
                btn_del.pack(side=tk.RIGHT)

            add_frame = tk.Frame(slot_container, bg="#f0f0f0")
            add_frame.pack(fill=tk.X, padx=10, pady=(0, 3))
            
            entry = ttk.Entry(add_frame, font=("Microsoft YaHei", 10))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.bind("<Return>", lambda e, idx=s_idx, ent=entry: self.add_task(idx, ent))
            
            btn_add = ttk.Button(add_frame, text="+", width=2, command=lambda idx=s_idx, ent=entry: self.add_task(idx, ent))
            btn_add.pack(side=tk.RIGHT)

    def change_date(self, days):
        def _change():
            curr = datetime.strptime(self.current_date, "%Y-%m-%d")
            new_date = curr + timedelta(days=days)
            self.current_date = new_date.strftime("%Y-%m-%d")
            if self.current_date not in self.data:
                self.data[self.current_date] = {"slots": [{"name": "上午", "tasks": []}, {"name": "下午", "tasks": []}], "checked_in": False, "day_completed": False}
            self.refresh_ui()
        return _change

    def jump_to_today(self):
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        if self.current_date not in self.data:
            self.data[self.current_date] = {"slots": [{"name": "上午", "tasks": []}, {"name": "下午", "tasks": []}], "checked_in": False, "day_completed": False}
        self.refresh_ui()

    def add_new_slot(self):
        name = simpledialog.askstring("新建时段", "输入时段名称 (如：中午、晚上、健身):", initialvalue="新时段")
        if name:
            slots = self.get_current_slots()
            slots.append({"name": name, "tasks": []})
            self.save_data()
            self.refresh_ui()

    def edit_slot_name(self, slot_idx):
        slots = self.get_current_slots()
        old_name = slots[slot_idx]["name"]
        new_name = simpledialog.askstring("编辑时段", "修改名称:", initialvalue=old_name)
        if new_name:
            slots[slot_idx]["name"] = new_name
            self.save_data()
            self.refresh_ui()

    def delete_slot(self, slot_idx):
        if messagebox.askyesno("确认", "确定删除此时段及所有任务吗？"):
            slots = self.get_current_slots()
            del slots[slot_idx]
            self.save_data()
            self.refresh_ui()

    def add_task(self, slot_idx, entry_widget):
        text = entry_widget.get().strip()
        if not text: return
        is_important = messagebox.askyesno("重要程度", f"任务：{text}\n\n是否标记为【重要事件 (*)】？")
        slots = self.get_current_slots()
        slots[slot_idx]["tasks"].append({"text": text, "done": False, "important": is_important})
        entry_widget.delete(0, tk.END)
        self.save_data()
        self.refresh_ui()

    def toggle_task(self, slot_idx, task_idx):
        slots = self.get_current_slots()
        task = slots[slot_idx]["tasks"][task_idx]
        task["done"] = not task["done"]
        self.save_data()
        self.refresh_ui()

    def edit_task(self, slot_idx, task_idx):
        slots = self.get_current_slots()
        task = slots[slot_idx]["tasks"][task_idx]
        new_text = simpledialog.askstring("编辑任务", "修改内容:", initialvalue=task["text"])
        if new_text is None: return
        current_imp = task.get("important", False)
        is_important = messagebox.askyesno("重要程度", "保持为【重要事件 (*)】吗？", initialvalue=current_imp)
        task["text"] = new_text.strip()
        task["important"] = is_important
        self.save_data()
        self.refresh_ui()

    def delete_task(self, slot_idx, task_idx):
        slots = self.get_current_slots()
        del slots[slot_idx]["tasks"][task_idx]
        self.save_data()
        self.refresh_ui()

    # 【核心修改】完成逻辑
    def finish_day(self):
        has_imp, all_imp_done = self.check_important_tasks_status(self.current_date)
        
        if not all_imp_done:
            messagebox.showwarning("无法完成", "⚠️ 还有重要任务 (*) 未完成！请先完成所有标星任务。")
            self.refresh_ui()
            return
        
        # 确认操作
        confirm = messagebox.askyesno("确认完成", "✅ 所有重要任务已完成！\n\n确定要标记今天为“已完成”吗？\n(这将计入月度统计，未完成的普通任务将自动留到明天或忽略)")
        
        if confirm:
            self.data[self.current_date]["day_completed"] = True
            self.save_data()
            self.refresh_ui()
            messagebox.showinfo("太棒了！", "🎉 今日已归档！月度完成数 +1")

    def hide_window(self):
        self.root.withdraw()
    
    def exit_app(self):
        if messagebox.askyesno("确认退出", "确定要退出程序吗？"):
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()
            self.save_data()
            self.root.destroy()
            os._exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = SmartTodoApp(root)
    root.mainloop()