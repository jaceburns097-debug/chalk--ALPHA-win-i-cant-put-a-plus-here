import tkinter as tk
from tkinter import scrolledtext
import threading
import re
import queue

class ChalkPlusPlusInterpreter:
    def __init__(self, ide):
        self.ide = ide
        self.variables = {}
        self.running = True

    def log(self, text, is_error=False, newline=True):
        tag = "error" if is_error else "normal"
        self.ide.terminal.config(state=tk.NORMAL)
        self.ide.terminal.insert(tk.END, str(text) + ("\n" if newline else ""), tag)
        self.ide.terminal.mark_set("input_start", "insert")
        self.ide.terminal.see(tk.END)
        self.ide.terminal.config(state=tk.DISABLED)

    def run_code(self, code):
        try:
            self.ide.terminal.config(state=tk.NORMAL)
            self.ide.terminal.delete(1.0, tk.END)
            self.ide.terminal.config(state=tk.DISABLED)
            self.variables = {} 
            self.running = True
            
            lines = [{"text": l.strip(), "orig": i+1} for i, l in enumerate(code.split('\n')) if l.strip() and not l.strip().startswith('^')]

            if not any("import chalk++" in l["text"] for l in lines):
                self.log("CRITICAL ERROR: 'import chalk++' missing!", True)
                return

            idx = 0
            while idx < len(lines) and self.running:
                line_text = lines[idx]["text"]
                if any(x in line_text for x in ["import", "int main()", "::"]):
                    idx += 1; continue
                
                if "while true" in line_text:
                    loop_start_idx = idx + 1
                    while self.running:
                        current_ptr = loop_start_idx
                        while current_ptr < len(lines) and self.running:
                            if lines[current_ptr]["text"] == "}": break
                            res, next_ptr = self.execute_logic(lines, current_ptr)
                            if res == "skip":
                                current_ptr = self.find_closing_brace(lines, current_ptr)
                            current_ptr += 1
                    break 

                res, next_ptr = self.execute_logic(lines, idx)
                if res == "skip":
                    idx = self.find_closing_brace(lines, idx)
                idx += 1
        except Exception as e: self.log(f"ENGINE ERROR: {e}", True)

    def execute_logic(self, lines, idx):
        line = lines[idx]["text"].replace(';', '').strip()
        if "input(" in line:
            var_name = line.split('=')[0].strip()
            prompt = re.search(r'input\("(.*?)"\)', line).group(1)
            self.variables[var_name] = self.ide.get_terminal_input(prompt)
            return "ok", idx
        if line.startswith("if "):
            match = re.search(r'if (.*?) [=]{1,2} "(.*?)"', line)
            if match:
                var, target = match.group(1).strip(), match.group(2).strip()
                current = str(self.variables.get(var, "nothing")).strip()
                if current.lower() != target.lower(): return "skip", idx
            return "ok", idx
        if line.startswith("print"):
            inner = re.search(r'\((.*?)\)', line).group(1).strip()
            val = self.variables.get(inner, inner.strip('"'))
            self.log(val)
            return "ok", idx
        if "=" in line and "if " not in line:
            parts = line.split('=')
            self.variables[parts[0].strip()] = parts[1].strip().strip('"')
        return "ok", idx

    def find_closing_brace(self, lines, start_idx):
        depth = 0
        for i in range(start_idx, len(lines)):
            if "{" in lines[i]["text"]: depth += 1
            if "}" in lines[i]["text"]: depth -= 1
            if depth == 0 and "}" in lines[i]["text"]: return i
        return start_idx

class ChalkIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Chalk++ Universal V1.001")
        self.root.geometry("1000x850")
        self.root.configure(bg="#1e1e1e")
        self.input_queue = queue.Queue()
        self.editor = scrolledtext.ScrolledText(root, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", font=("Consolas", 13))
        self.editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.terminal = scrolledtext.ScrolledText(root, height=12, bg="black", fg="#00ff00", font=("Consolas", 12), state=tk.DISABLED)
        self.terminal.pack(fill=tk.X, padx=10, pady=5)
        self.status = tk.Label(root, text="READY", bg="#333", fg="white", font=("Arial", 10, "bold"))
        self.status.pack(fill=tk.X)
        self.terminal.bind("<Return>", self.handle_enter)
        
   
        self.terminal.bind("<BackSpace>", lambda e: None) 

        btns = tk.Frame(root, bg="#1e1e1e")
        btns.pack(fill=tk.X)
        tk.Button(btns, text="RUN", command=self.execute, bg="#2ea043", fg="white", width=15).pack(side=tk.LEFT, padx=10, pady=5)
        tk.Button(btns, text="STOP", command=self.stop, bg="#d73a49", fg="white", width=15).pack(side=tk.LEFT, pady=5)
        self.interpreter = ChalkPlusPlusInterpreter(self)

    def handle_enter(self, event):
        if self.terminal.cget("state") == tk.NORMAL:
            txt = self.terminal.get("input_start", "end-1c").strip()
            self.input_queue.put(txt)
            self.terminal.config(state=tk.NORMAL)
            self.terminal.insert(tk.END, "\n")
            self.terminal.mark_set("input_start", "insert")
            self.terminal.config(state=tk.DISABLED)
            return "break"

    def get_terminal_input(self, prompt):
        self.interpreter.log(prompt, newline=False)
        self.status.config(text="LISTENING...", bg="#ffd700", fg="black")
        self.terminal.config(state=tk.NORMAL)
        self.terminal.focus_set()
        self.terminal.mark_set("insert", "end")
        self.terminal.mark_set("input_start", "insert")
        val = self.input_queue.get()
        self.status.config(text="RUNNING...", bg="#2ea043", fg="white")
        return val

    def stop(self):
        self.interpreter.running = False
        self.input_queue.put("")

    def execute(self):
        code = self.editor.get(1.0, tk.END).strip()
        threading.Thread(target=self.interpreter.run_code, args=(code,), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk(); app = ChalkIDE(root); root.mainloop()
