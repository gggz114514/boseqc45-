import os
import sys
import time
import shutil
import logging
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ======================== 日志配置 ========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ======================== GUI 类 ========================
class FirmwareMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("固件监控器")
        self.root.geometry("600x450")

        self.firmware_path = None
        self.monitor_directory = os.path.join(os.environ.get("TEMP") or tempfile.gettempdir())
        self.pattern = "Bose Updater"

        self.setup_ui()

        self.observer = Observer()
        self.event_handler = CustomFileSystemEventHandler(self)

    def setup_ui(self):
        # 固件选择部分
        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        tk.Label(frame, text="选择固件:").pack(side=tk.LEFT, padx=5)

        # 动态加载 firmware 目录下所有 .bin 文件
        firmware_dir = os.path.join(os.getcwd(), "firmware")
        if not os.path.exists(firmware_dir):
            os.makedirs(firmware_dir)
        self.firmware_options = [f for f in os.listdir(firmware_dir) if f.endswith(".bin")]
        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(frame, textvariable=self.combo_var, values=self.firmware_options, state="readonly")
        self.combo.pack(side=tk.LEFT)
        self.combo.bind("<<ComboboxSelected>>", self.use_selected_firmware)

        tk.Button(frame, text="浏览...", command=self.select_firmware).pack(side=tk.LEFT, padx=5)

        self.selected_label = tk.Label(self.root, text="未选择固件文件")
        self.selected_label.pack()

        # 显示路径和前缀
        tk.Label(self.root, text=f"监控路径: {self.monitor_directory}").pack()
        tk.Label(self.root, text=f"文件名前缀: {self.pattern}").pack()

        # 日志窗口
        self.status_box = scrolledtext.ScrolledText(self.root, height=15, state='disabled')
        self.status_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.start_button = tk.Button(self.root, text="开始监控", command=self.start_monitoring)
        self.start_button.pack(pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def log(self, message):
        self.status_box.config(state='normal')
        self.status_box.insert(tk.END, message + "\n")
        self.status_box.yview(tk.END)
        self.status_box.config(state='disabled')
        logger.info(message)

    def use_selected_firmware(self, event=None):
        filename = self.combo_var.get()
        full_path = os.path.join(os.getcwd(), "firmware", filename)
        if os.path.exists(full_path):
            self.firmware_path = full_path
            self.selected_label.config(text=f"已选择固件文件: {full_path}")
            self.log(f"已选择固件文件: {full_path}")
        else:
            self.firmware_path = None
            self.selected_label.config(text="文件不存在")
            self.log("选择的固件文件不存在")

    def select_firmware(self):
        path = filedialog.askopenfilename(
            title="选择固件文件",
            filetypes=[("Binary Files", "*.bin"), ("All Files", "*.")]
        )
        if path:
            self.firmware_path = path
            self.combo.set("")  # 清空下拉框选择
            self.selected_label.config(text=f"已选择固件文件: {path}")
            self.log(f"已选择固件文件: {path}")

    def start_monitoring(self):
        if not self.firmware_path:
            messagebox.showwarning("未选择固件", "请先选择固件文件")
            return

        self.log(f"开始监控目录: {self.monitor_directory}")
        self.observer.schedule(self.event_handler, self.monitor_directory, recursive=False)
        self.observer.start()
        self.start_button.config(state='disabled')

    def stop_monitoring(self):
        self.observer.stop()
        self.observer.join()

    def on_close(self):
        if self.observer.is_alive():
            self.stop_monitoring()
        self.root.destroy()

# ======================== 文件系统事件处理类 ========================
class CustomFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)
        if filename.startswith(self.app.pattern):
            self.app.log(f"检测到文件: {filename}")
            full_path = os.path.join(self.app.monitor_directory, filename)

            # 等待文件写入完成
            threading.Thread(target=self.copy_firmware_when_ready, args=(full_path,)).start()

    def copy_firmware_when_ready(self, target_path):
        while True:
            try:
                initial_size = os.path.getsize(target_path)
                time.sleep(0.5)
                final_size = os.path.getsize(target_path)
                if initial_size == final_size and initial_size > 0:
                    break
            except FileNotFoundError:
                time.sleep(0.5)

        try:
            shutil.copy(self.app.firmware_path, target_path)
            self.app.log(f"固件已复制到: {target_path}")
        except Exception as e:
            self.app.log(f"复制出错: {e}")

# ======================== 主函数 ========================
def main():
    root = tk.Tk()
    app = FirmwareMonitorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
