import os
import datetime


class _Logger:
    def init(self, debug, file):
        self.debug = debug
        self.file = file;
        log_dir = os.path.dirname(self.file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception as e:
                raise RuntimeError(f"无法创建日志目录 {log_dir}: {e}")
    
    def info(self, message):
        self.log_print("info", message)

    def warn(self, message):
        self.log_print("warn", message)
    
    def error(self, message):
        self.log_print("error", message)

    def log_print(self, level, message):
        if not self.debug:
            return
        timestamp = datetime.datetime.now().strftime(r"%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} {level} : {message}\n"
        with open(self.file, "a", encoding="utf-8") as f:
            f.write(log_entry)


logger = _Logger()
