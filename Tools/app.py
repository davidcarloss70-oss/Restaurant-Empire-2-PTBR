import customtkinter as ctk
import json
import os
import shutil
import threading
import sys
import io
import zipfile
import subprocess
from tkinter import filedialog, messagebox

# Add tools directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_config.json")
CACHE_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translation_cache.json")

# Patch structure: (zip_internal_path, relative_to_game_root)
PATCH_STRUCTURE = [
    ("resource", "resource"),
    ("tutorial", "tutorial"),
    ("script/extracted", "script/extracted"),
]

# ── helpers ──────────────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"game_path": ""}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def find_zip():
    """Locate RE2_PTBR_Patch.zip: next to app.py or one folder up."""
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in [here, os.path.dirname(here)]:
        p = os.path.join(candidate, "RE2_PTBR_Patch.zip")
        if os.path.exists(p):
            return p
    return None

# ── stdout redirect ───────────────────────────────────────────────────────────

class RedirectText(io.StringIO):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def write(self, s):
        self.widget.after(0, self._append, s)

    def _append(self, s):
        self.widget.configure(state="normal")
        self.widget.insert("end", s)
        self.widget.see("end")

    def flush(self):
        pass

# ── main app ─────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RE2 PT-BR Modding Tool")
        self.geometry("1050x680")
        self.minsize(900, 600)

        self.cfg        = load_config()
        self.cache_data = {}
        self.filtered_keys = []
        self.selected_key  = None
        self.item_widgets  = []

        self._build_ui()
        self.load_cache()
        self.show_view("editor")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── TOP BAR: game path ───────────────────────────────────────────────
        top = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray15"))
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="📁 Pasta do Jogo:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=(15, 5), pady=10)

        self.path_entry = ctk.CTkEntry(top, placeholder_text="Ex: C:\\...\\Restaurant Empire 2")
        self.path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=10)
        if self.cfg.get("game_path"):
            self.path_entry.insert(0, self.cfg["game_path"])

        ctk.CTkButton(top, text="Procurar", width=90, command=self.browse_game).grid(
            row=0, column=2, padx=5, pady=10)
        ctk.CTkButton(top, text="Salvar Caminho", width=110, fg_color="#1a6b9c",
                      hover_color="#155c87", command=self.save_game_path).grid(
            row=0, column=3, padx=(0, 15), pady=10)

        # ── SIDEBAR ──────────────────────────────────────────────────────────
        side = ctk.CTkFrame(self, width=180, corner_radius=0)
        side.grid(row=1, column=0, sticky="nsew")
        side.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(side, text="RE2 Tradutor",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 15))

        self._sidebar_btn(side, "📝  Editor de Textos",  1, lambda: self.show_view("editor"))
        self._sidebar_btn(side, "📂  Arquivos do Patch",  2, lambda: self.show_view("files"))
        self._sidebar_btn(side, "📋  Console Log",        3, lambda: self.show_view("log"))

        ctk.CTkFrame(side, height=2, fg_color="gray40").grid(
            row=4, column=0, sticky="ew", padx=15, pady=10)

        ctk.CTkButton(side, text="✅  Aplicar Patch",
                      fg_color="#28a745", hover_color="#218838",
                      font=ctk.CTkFont(weight="bold"),
                      command=self.apply_patch).grid(
            row=5, column=0, padx=15, pady=5, sticky="ew")

        ctk.CTkButton(side, text="↩️  Restaurar Inglês",
                      fg_color="#c0392b", hover_color="#a93226",
                      command=self.restore_english).grid(
            row=6, column=0, padx=15, pady=(5, 20), sticky="s")

        # ── MAIN AREA ────────────────────────────────────────────────────────
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=15, pady=15)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self._build_editor_view()
        self._build_files_view()
        self._build_log_view()

    def _sidebar_btn(self, parent, text, row, cmd):
        ctk.CTkButton(parent, text=text, anchor="w", command=cmd,
                      fg_color="transparent", hover_color=("gray75", "gray30")).grid(
            row=row, column=0, padx=10, pady=3, sticky="ew")

    # ── Editor view ───────────────────────────────────────────────────────────

    def _build_editor_view(self):
        self.editor_view = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.editor_view.grid_rowconfigure(1, weight=1)
        self.editor_view.grid_columnconfigure(0, weight=1)

        # search
        sf = ctk.CTkFrame(self.editor_view, fg_color="transparent")
        sf.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        sf.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(sf,
            placeholder_text="🔍  Pesquisar texto original (EN) ou traduzido (PT)…")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)

        ctk.CTkLabel(sf, text="", width=5).grid(row=0, column=1)
        self.lbl_count = ctk.CTkLabel(sf, text="", text_color="gray", width=120)
        self.lbl_count.grid(row=0, column=2)

        # list
        self.list_frame = ctk.CTkScrollableFrame(self.editor_view, corner_radius=8)
        self.list_frame.grid(row=1, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        # edit box
        ef = ctk.CTkFrame(self.editor_view, corner_radius=8)
        ef.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ef.grid_columnconfigure(0, weight=1)

        self.lbl_editing = ctk.CTkLabel(ef,
            text="Selecione um texto acima para editar", text_color="gray")
        self.lbl_editing.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))

        self.txt_edit = ctk.CTkTextbox(ef, height=70)
        self.txt_edit.grid(row=1, column=0, sticky="ew", padx=10, pady=4)

        self.btn_save = ctk.CTkButton(ef, text="💾  Salvar Tradução",
                                      command=self.save_translation, state="disabled")
        self.btn_save.grid(row=2, column=0, sticky="e", padx=10, pady=(0, 10))

    # ── Files view ────────────────────────────────────────────────────────────

    def _build_files_view(self):
        self.files_view = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.files_view.grid_rowconfigure(1, weight=1)
        self.files_view.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.files_view,
            text="Arquivos que serão instalados pelo Patch (apenas os traduzidos)",
            font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8))

        self.files_tree = ctk.CTkScrollableFrame(self.files_view, corner_radius=8)
        self.files_tree.grid(row=1, column=0, sticky="nsew")
        self.files_tree.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(self.files_view, text="🔄  Atualizar lista",
                      command=self.refresh_files_view).grid(
            row=2, column=0, sticky="e", pady=(8, 0))

    # ── Log view ──────────────────────────────────────────────────────────────

    def _build_log_view(self):
        self.log_view = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.log_view.grid_rowconfigure(0, weight=1)
        self.log_view.grid_columnconfigure(0, weight=1)

        self.log_textbox = ctk.CTkTextbox(self.log_view, corner_radius=8,
                                          font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

        ctk.CTkButton(self.log_view, text="Limpar log", width=100,
                      command=lambda: self.log_textbox.delete("1.0", "end")).grid(
            row=1, column=0, sticky="e", pady=(5, 0))

    # ── View switching ────────────────────────────────────────────────────────

    def show_view(self, name):
        for v in (self.editor_view, self.files_view, self.log_view):
            v.grid_forget()
        if name == "editor":
            self.editor_view.grid(row=0, column=0, sticky="nsew")
        elif name == "files":
            self.files_view.grid(row=0, column=0, sticky="nsew")
            self.refresh_files_view()
        elif name == "log":
            self.log_view.grid(row=0, column=0, sticky="nsew")

    # ── Game path ─────────────────────────────────────────────────────────────

    def browse_game(self):
        path = filedialog.askdirectory(title="Selecione a pasta raiz do Restaurant Empire 2")
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    def save_game_path(self):
        path = self.path_entry.get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showerror("Erro", "Pasta inválida ou não encontrada.")
            return
        self.cfg["game_path"] = path
        save_config(self.cfg)
        messagebox.showinfo("Salvo", f"Caminho salvo:\n{path}")

    def get_game_path(self):
        p = self.path_entry.get().strip()
        if not p:
            p = self.cfg.get("game_path", "")
        return p

    # ── Cache ─────────────────────────────────────────────────────────────────

    def load_cache(self):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                self.cache_data = json.load(f)
            self.filtered_keys = list(self.cache_data.keys())
            self.render_list()
        except Exception as e:
            self.lbl_editing.configure(
                text=f"Erro ao carregar cache: {e}", text_color="red")

    def on_search(self, event=None):
        q = self.search_entry.get().lower()
        if not q:
            self.filtered_keys = list(self.cache_data.keys())
        else:
            self.filtered_keys = [
                k for k in self.cache_data
                if q in k.lower() or (self.cache_data[k] and q in self.cache_data[k].lower())
            ]
        self.render_list()

    def render_list(self):
        for w in self.item_widgets:
            w.destroy()
        self.item_widgets.clear()

        keys = self.filtered_keys[:100]
        self.lbl_count.configure(
            text=f"{len(self.filtered_keys):,} resultado(s)")

        if not keys:
            lbl = ctk.CTkLabel(self.list_frame,
                               text="Nenhum resultado.", text_color="gray")
            lbl.grid(row=0, column=0, pady=20)
            self.item_widgets.append(lbl)
            return

        for i, key in enumerate(keys):
            val = self.cache_data[key] or "[Não traduzido]"
            row_frame = ctk.CTkFrame(self.list_frame,
                                     fg_color=("gray85", "gray22"), corner_radius=5)
            row_frame.grid(row=i, column=0, sticky="ew", pady=2, padx=4)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.bind("<Button-1>", lambda e, k=key: self.select_item(k))

            en = ctk.CTkLabel(row_frame,
                              text=f"🇺🇸  {key[:70]}…" if len(key) > 70 else f"🇺🇸  {key}",
                              text_color="gray", justify="left", anchor="w")
            en.grid(row=0, column=0, sticky="w", padx=10, pady=(4, 0))
            en.bind("<Button-1>", lambda e, k=key: self.select_item(k))

            pt_txt = val[:90] + "…" if len(val) > 90 else val
            pt = ctk.CTkLabel(row_frame, text=f"🇧🇷  {pt_txt}",
                              justify="left", anchor="w",
                              font=ctk.CTkFont(weight="bold"))
            pt.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))
            pt.bind("<Button-1>", lambda e, k=key: self.select_item(k))

            self.item_widgets.append(row_frame)

    def select_item(self, key):
        self.selected_key = key
        self.lbl_editing.configure(
            text=f"Editando →  {key[:80]}", text_color="#3de080")
        self.txt_edit.delete("1.0", "end")
        val = self.cache_data.get(key, "")
        if val:
            self.txt_edit.insert("1.0", val)
        self.btn_save.configure(state="normal")
        self.show_view("editor")

    def save_translation(self):
        if not self.selected_key:
            return
        new_val = self.txt_edit.get("1.0", "end").strip()
        self.cache_data[self.selected_key] = new_val
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            self.lbl_editing.configure(text="✅  Salvo com sucesso!", text_color="#28a745")
            self.render_list()
        except Exception as e:
            self.lbl_editing.configure(text=f"Erro ao salvar: {e}", text_color="red")

    # ── Files view refresh ────────────────────────────────────────────────────

    def refresh_files_view(self):
        for w in self.files_tree.winfo_children():
            w.destroy()

        zip_path = find_zip()
        if not zip_path:
            ctk.CTkLabel(self.files_tree,
                         text="RE2_PTBR_Patch.zip não encontrado.",
                         text_color="red").grid(row=0, column=0, pady=20)
            return

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = sorted(zf.namelist())
        except Exception as e:
            ctk.CTkLabel(self.files_tree, text=f"Erro: {e}",
                         text_color="red").grid(row=0, column=0)
            return

        # group by folder
        folders = {}
        for n in names:
            parts = n.split("/")
            folder = "/".join(parts[:-1]) if len(parts) > 1 else "(raiz)"
            folders.setdefault(folder, []).append(parts[-1])

        row = 0
        for folder, files in sorted(folders.items()):
            ctk.CTkLabel(self.files_tree,
                         text=f"📁  {folder}/",
                         font=ctk.CTkFont(weight="bold"),
                         text_color="#3de080").grid(
                row=row, column=0, sticky="w", padx=5, pady=(10, 2))
            row += 1
            for fname in files:
                ctk.CTkLabel(self.files_tree,
                             text=f"    📄  {fname}",
                             text_color="gray").grid(
                    row=row, column=0, sticky="w", padx=15, pady=1)
                row += 1

    # ── Apply patch ───────────────────────────────────────────────────────────

    def apply_patch(self):
        game_path = self.get_game_path()
        if not game_path or not os.path.isdir(game_path):
            messagebox.showerror("Erro",
                "Configure a pasta do jogo primeiro!\n\n"
                "Clique em 'Procurar' ou digite o caminho e salve.")
            return

        zip_path = find_zip()
        if not zip_path:
            messagebox.showerror("Erro",
                "RE2_PTBR_Patch.zip não encontrado.\n"
                "Coloque o ZIP na mesma pasta que o app.")
            return

        self.show_view("log")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", "=== APLICANDO PATCH PT-BR ===\n\n")
        threading.Thread(target=self._do_apply,
                         args=(game_path, zip_path), daemon=True).start()

    def _do_apply(self, game_path, zip_path):
        redir = RedirectText(self.log_textbox)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                total = len([n for n in names if not n.endswith("/")])
                done  = 0

                for name in names:
                    if name.endswith("/"):
                        continue
                    dest = os.path.join(game_path, name.replace("/", os.sep))
                    os.makedirs(os.path.dirname(dest), exist_ok=True)

                    # create .bak if original doesn't have one yet
                    bak = dest + ".bak"
                    if not os.path.exists(bak) and os.path.exists(dest) and not dest.endswith(".bak"):
                        shutil.copy2(dest, bak)

                    with zf.open(name) as src, open(dest, "wb") as out:
                        out.write(src.read())

                    done += 1
                    redir.write(f"  [{done}/{total}]  {name}\n")

            redir.write("\n✅  PATCH APLICADO COM SUCESSO!\n")
            redir.write(f"📁  Pasta do jogo: {game_path}\n")
        except Exception as e:
            redir.write(f"\n❌  ERRO: {e}\n")

    # ── Restore English ───────────────────────────────────────────────────────

    def restore_english(self):
        game_path = self.get_game_path()
        if not game_path or not os.path.isdir(game_path):
            messagebox.showerror("Erro", "Configure a pasta do jogo primeiro!")
            return

        if not messagebox.askyesno("Restaurar Inglês",
            "Isso vai restaurar os arquivos originais em inglês a partir dos backups (.bak).\n\n"
            "Tem certeza?"):
            return

        self.show_view("log")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", "=== RESTAURANDO INGLÊS ===\n\n")
        threading.Thread(target=self._do_restore,
                         args=(game_path,), daemon=True).start()

    def _do_restore(self, game_path):
        redir = RedirectText(self.log_textbox)
        restored = 0
        missing  = 0

        # Walk all subfolders looking for .bak files that match translated files
        for root, dirs, files in os.walk(game_path):
            for fname in files:
                if not fname.endswith(".bak"):
                    continue
                bak  = os.path.join(root, fname)
                orig = bak[:-4]  # remove .bak
                if os.path.exists(orig):
                    shutil.copy2(bak, orig)
                    rel = os.path.relpath(orig, game_path)
                    redir.write(f"  ↩️  {rel}\n")
                    restored += 1
                else:
                    missing += 1

        redir.write(f"\n✅  {restored} arquivo(s) restaurados para inglês.\n")
        if missing:
            redir.write(f"⚠️   {missing} backup(s) sem arquivo alvo (ignorados).\n")


if __name__ == "__main__":
    app = App()
    app.mainloop()
