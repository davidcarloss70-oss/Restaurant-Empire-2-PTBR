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

# ── BASE_DIR: sempre aponta para a pasta do .exe (ou do script .py) ──────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

CONFIG_FILE       = os.path.join(BASE_DIR, "app_config.json")
CACHE_FILE        = os.path.join(BASE_DIR, "translation_cache.json")
CACHE_BACKUP_FILE = os.path.join(BASE_DIR, "translation_cache.backup.json")

# Scripts que geram os arquivos binários a partir do cache
SCRIPTS = ["translate_all_safe.py", "translate_std_set.py", "translate_tutorials.py"]

# ── helpers ───────────────────────────────────────────────────────────────────

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
    """Localiza RE2_PTBR_Patch.zip: mesma pasta do .exe ou pasta acima."""
    for folder in [BASE_DIR, os.path.dirname(BASE_DIR)]:
        p = os.path.join(folder, "RE2_PTBR_Patch.zip")
        if os.path.exists(p):
            return p
    return None

def scripts_available():
    """Verifica se os scripts de tradução estão disponíveis na pasta do app."""
    return all(os.path.exists(os.path.join(BASE_DIR, s)) for s in SCRIPTS)

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

# ── main app ──────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RE2 PT-BR Modding Tool")
        self.geometry("1050x700")
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
        self.grid_rowconfigure(2, weight=0)   # footer row
        self.grid_columnconfigure(1, weight=1)

        # ── TOP BAR: game path ───────────────────────────────────────────────
        top = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray15"))
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
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
        side = ctk.CTkFrame(self, width=185, corner_radius=0)
        side.grid(row=1, column=0, sticky="nsew")
        side.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(side, text="RE2 Tradutor",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 15))

        self._sidebar_btn(side, "📝  Editor de Textos",   1, lambda: self.show_view("editor"))
        self._sidebar_btn(side, "📦  Patch Original",      2, lambda: self.show_view("patch"))
        self._sidebar_btn(side, "📋  Console Log",         3, lambda: self.show_view("log"))

        ctk.CTkFrame(side, height=2, fg_color="gray40").grid(
            row=4, column=0, sticky="ew", padx=15, pady=10)

        ctk.CTkButton(side, text="↩️  Restaurar Inglês",
                      fg_color="#c0392b", hover_color="#a93226",
                      command=self.restore_english).grid(
            row=5, column=0, padx=15, pady=(5, 20), sticky="s")

        # ── MAIN AREA ────────────────────────────────────────────────────────
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=15, pady=15)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self._build_editor_view()
        self._build_patch_view()
        self._build_log_view()
        self._build_footer()

    def _build_footer(self):
        footer = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "gray13"), height=28)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_propagate(False)

        ctk.CTkLabel(footer,
            text="RE2 PT-BR Modding Tool  •  Tradução por davidcarloss  •  github.com/davidcarloss70-oss",
            text_color="gray", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="e", padx=15)

    def _sidebar_btn(self, parent, text, row, cmd):
        ctk.CTkButton(parent, text=text, anchor="w", command=cmd,
                      fg_color="transparent", hover_color=("gray75", "gray30")).grid(
            row=row, column=0, padx=10, pady=3, sticky="ew")

    # ── Editor view ───────────────────────────────────────────────────────────

    def _build_editor_view(self):
        self.editor_view = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.editor_view.grid_rowconfigure(1, weight=1)
        self.editor_view.grid_columnconfigure(0, weight=1)

        # Header com botão de aplicar edições
        hdr = ctk.CTkFrame(self.editor_view, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        hdr.grid_columnconfigure(0, weight=1)

        sf = ctk.CTkFrame(hdr, fg_color="transparent")
        sf.grid(row=0, column=0, sticky="ew")
        sf.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(sf,
            placeholder_text="🔍  Pesquisar texto original (EN) ou traduzido (PT)…")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.lbl_count = ctk.CTkLabel(sf, text="", text_color="gray", width=130)
        self.lbl_count.grid(row=0, column=1, padx=(8, 0))

        # Botão "Aplicar Edições no Jogo" no canto direito
        self.btn_apply_edits = ctk.CTkButton(hdr,
            text="🚀  Aplicar Edições no Jogo",
            fg_color="#1a6b9c", hover_color="#155c87",
            font=ctk.CTkFont(weight="bold"),
            command=self.apply_cache_edits)
        self.btn_apply_edits.grid(row=0, column=1, padx=(12, 0))

        # Aviso sobre scripts
        if not scripts_available():
            ctk.CTkLabel(self.editor_view,
                text="ℹ️  Para aplicar edições do cache, coloque os scripts Python na mesma pasta do .exe "
                     "ou use o 'Patch Original' para reinstalar a tradução base.",
                text_color="#f0a500", wraplength=700, justify="left").grid(
                row=2, column=0, sticky="w", pady=(0, 4))

        # list
        self.list_frame = ctk.CTkScrollableFrame(self.editor_view, corner_radius=8)
        self.list_frame.grid(row=3, column=0, sticky="nsew")
        self.editor_view.grid_rowconfigure(3, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # edit box
        ef = ctk.CTkFrame(self.editor_view, corner_radius=8)
        ef.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ef.grid_columnconfigure(0, weight=1)

        # linha de status/backup do cache
        bak_row = ctk.CTkFrame(ef, fg_color="transparent")
        bak_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
        bak_row.grid_columnconfigure(0, weight=1)

        self.lbl_editing = ctk.CTkLabel(bak_row,
            text="Selecione um texto acima para editar", text_color="gray")
        self.lbl_editing.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(bak_row, text="🔄  Restaurar Cache Backup",
                      width=190, fg_color="#7d3c98", hover_color="#6c3483",
                      command=self.restore_cache_backup).grid(row=0, column=1, padx=(8, 0))

        self.txt_edit = ctk.CTkTextbox(ef, height=65)
        self.txt_edit.grid(row=1, column=0, sticky="ew", padx=10, pady=4)

        btn_row = ctk.CTkFrame(ef, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.btn_save = ctk.CTkButton(btn_row, text="💾  Salvar no Cache",
                                      command=self.save_translation, state="disabled")
        self.btn_save.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(btn_row, text="← salva a edição no cache  |  use 'Aplicar Edições' para enviar ao jogo",
                     text_color="gray", font=ctk.CTkFont(size=11)).grid(
            row=0, column=1, padx=(12, 0), sticky="w")

    # ── Patch Original view ───────────────────────────────────────────────────

    def _build_patch_view(self):
        self.patch_view = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.patch_view.grid_rowconfigure(2, weight=1)
        self.patch_view.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(self.patch_view,
            text="📦  Patch Original — Tradução Completa (ZIP)",
            font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 6))

        # Description box
        desc = ctk.CTkFrame(self.patch_view,
                            fg_color=("gray85", "gray20"), corner_radius=8)
        desc.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        desc.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(desc,
            text=(
                "Este é o backup da tradução completa em PT-BR.\n"
                "• Use 'Aplicar Patch Original' para (re)instalar a tradução completa no jogo.\n"
                "• Se fez edições no cache e algo deu errado, aplique este patch para restaurar a tradução base.\n"
                "• Para voltar ao inglês, use o botão '↩️ Restaurar Inglês' na barra lateral."
            ),
            text_color="gray", justify="left", anchor="w", wraplength=700).grid(
            row=0, column=0, sticky="w", padx=15, pady=10)

        # Apply button
        btn_row = ctk.CTkFrame(desc, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 12))

        ctk.CTkButton(btn_row,
            text="✅  Aplicar Patch Original no Jogo",
            fg_color="#28a745", hover_color="#218838",
            font=ctk.CTkFont(weight="bold"),
            command=self.apply_original_patch).grid(row=0, column=0, padx=(0, 12))

        self.lbl_zip_status = ctk.CTkLabel(btn_row, text="", text_color="gray")
        self.lbl_zip_status.grid(row=0, column=1)

        # File list
        ctk.CTkLabel(self.patch_view,
            text="Conteúdo do ZIP:", text_color="gray").grid(
            row=2, column=0, sticky="w", pady=(0, 4))

        self.files_tree = ctk.CTkScrollableFrame(self.patch_view, corner_radius=8)
        self.files_tree.grid(row=3, column=0, sticky="nsew")
        self.patch_view.grid_rowconfigure(3, weight=1)
        self.files_tree.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(self.patch_view, text="🔄  Atualizar lista",
                      command=self.refresh_patch_view).grid(
            row=4, column=0, sticky="e", pady=(6, 0))

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
        for v in (self.editor_view, self.patch_view, self.log_view):
            v.grid_forget()
        if name == "editor":
            self.editor_view.grid(row=0, column=0, sticky="nsew")
        elif name == "patch":
            self.patch_view.grid(row=0, column=0, sticky="nsew")
            self.refresh_patch_view()
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
        self.filtered_keys = [
            k for k in self.cache_data
            if not q or q in k.lower() or (self.cache_data[k] and q in self.cache_data[k].lower())
        ]
        self.render_list()

    def render_list(self):
        for w in self.item_widgets:
            w.destroy()
        self.item_widgets.clear()

        keys = self.filtered_keys[:100]
        self.lbl_count.configure(text=f"{len(self.filtered_keys):,} resultado(s)")

        if not keys:
            lbl = ctk.CTkLabel(self.list_frame, text="Nenhum resultado.", text_color="gray")
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

            en_text = f"🇺🇸  {key[:70]}…" if len(key) > 70 else f"🇺🇸  {key}"
            en = ctk.CTkLabel(row_frame, text=en_text,
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
        self.lbl_editing.configure(text=f"Editando →  {key[:80]}", text_color="#3de080")
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
            # Backup automático antes de salvar
            if os.path.exists(CACHE_FILE):
                shutil.copy2(CACHE_FILE, CACHE_BACKUP_FILE)

            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            self.lbl_editing.configure(text="✅  Salvo no cache! (backup criado)", text_color="#28a745")
            self.render_list()
        except Exception as e:
            self.lbl_editing.configure(text=f"Erro ao salvar: {e}", text_color="red")

    def restore_cache_backup(self):
        if not os.path.exists(CACHE_BACKUP_FILE):
            messagebox.showinfo("Sem backup",
                "Nenhum backup de cache encontrado.\n"
                "O backup é criado automaticamente ao salvar uma tradução.")
            return
        if not messagebox.askyesno("Restaurar Cache Backup",
            "Isso vai restaurar o cache para a versão anterior à última edição salva.\n\n"
            "Tem certeza?"):
            return
        try:
            shutil.copy2(CACHE_BACKUP_FILE, CACHE_FILE)
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                self.cache_data = json.load(f)
            self.filtered_keys = list(self.cache_data.keys())
            self.render_list()
            self.lbl_editing.configure(
                text="✅  Cache restaurado para o backup!", text_color="#28a745")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao restaurar backup: {e}")

    # ── Apply cache edits (runs Python scripts) ───────────────────────────────

    def apply_cache_edits(self):
        game_path = self.get_game_path()
        if not game_path or not os.path.isdir(game_path):
            messagebox.showerror("Erro",
                "Configure a pasta do jogo primeiro!\n\n"
                "Clique em 'Procurar' na barra superior.")
            return

        if not scripts_available():
            messagebox.showinfo("Scripts não encontrados",
                "Os scripts Python de tradução não estão na pasta do aplicativo.\n\n"
                "Para aplicar edições do cache, coloque os arquivos .py na mesma pasta que o .exe:\n"
                "  • translate_all_safe.py\n"
                "  • translate_std_set.py\n"
                "  • translate_tutorials.py\n\n"
                "Alternativamente, use 'Patch Original' para reinstalar a tradução base.")
            return

        self.show_view("log")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", "=== APLICANDO EDIÇÕES DO CACHE ===\n\n")
        self.btn_apply_edits.configure(state="disabled", text="Aplicando…")
        threading.Thread(target=self._run_scripts, daemon=True).start()

    def _run_scripts(self):
        redir = RedirectText(self.log_textbox)
        old_stdout = sys.stdout
        sys.stdout = redir
        try:
            for script_name in SCRIPTS:
                script_path = os.path.join(BASE_DIR, script_name)
                redir.write(f"\n>> Executando {script_name}...\n")
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True, text=True, cwd=BASE_DIR)
                if result.stdout:
                    redir.write(result.stdout)
                if result.returncode != 0:
                    redir.write(f"\nERRO: {result.stderr}\n")
                    return
            redir.write("\n✅  EDIÇÕES APLICADAS COM SUCESSO!\n")
        except Exception as e:
            redir.write(f"\n❌  ERRO: {e}\n")
        finally:
            sys.stdout = old_stdout
            self.after(0, lambda: self.btn_apply_edits.configure(
                state="normal", text="🚀  Aplicar Edições no Jogo"))

    # ── Apply original patch (from ZIP) ──────────────────────────────────────

    def apply_original_patch(self):
        game_path = self.get_game_path()
        if not game_path or not os.path.isdir(game_path):
            messagebox.showerror("Erro",
                "Configure a pasta do jogo primeiro!")
            return

        zip_path = find_zip()
        if not zip_path:
            self.lbl_zip_status.configure(
                text="❌  RE2_PTBR_Patch.zip não encontrado!", text_color="red")
            return

        self.show_view("log")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", "=== APLICANDO PATCH ORIGINAL (ZIP) ===\n\n")
        threading.Thread(target=self._do_apply_zip,
                         args=(game_path, zip_path), daemon=True).start()

    def _do_apply_zip(self, game_path, zip_path):
        redir = RedirectText(self.log_textbox)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                files = [n for n in names if not n.endswith("/")]
                for i, name in enumerate(files, 1):
                    dest = os.path.join(game_path, name.replace("/", os.sep))
                    os.makedirs(os.path.dirname(dest), exist_ok=True)

                    # Cria backup .bak se ainda não existir
                    bak = dest + ".bak"
                    if not os.path.exists(bak) and os.path.exists(dest) and not dest.endswith(".bak"):
                        shutil.copy2(dest, bak)

                    with zf.open(name) as src, open(dest, "wb") as out:
                        out.write(src.read())

                    redir.write(f"  [{i}/{len(files)}]  {name}\n")

            redir.write("\n✅  PATCH ORIGINAL APLICADO COM SUCESSO!\n")
            redir.write(f"📁  Pasta do jogo: {game_path}\n")
        except Exception as e:
            redir.write(f"\n❌  ERRO: {e}\n")

    # ── Patch Original view ───────────────────────────────────────────────────

    def refresh_patch_view(self):
        for w in self.files_tree.winfo_children():
            w.destroy()

        zip_path = find_zip()
        if not zip_path:
            self.lbl_zip_status.configure(
                text="❌  ZIP não encontrado na pasta do app", text_color="red")
            ctk.CTkLabel(self.files_tree,
                         text="RE2_PTBR_Patch.zip não encontrado.\n"
                              "Coloque-o na mesma pasta que o .exe.",
                         text_color="red").grid(row=0, column=0, pady=20)
            return

        self.lbl_zip_status.configure(
            text=f"✅  {os.path.basename(zip_path)}", text_color="#3de080")

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = sorted(zf.namelist())
        except Exception as e:
            ctk.CTkLabel(self.files_tree, text=f"Erro: {e}",
                         text_color="red").grid(row=0, column=0)
            return

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

    # ── Restore English ───────────────────────────────────────────────────────

    def restore_english(self):
        game_path = self.get_game_path()
        if not game_path or not os.path.isdir(game_path):
            messagebox.showerror("Erro", "Configure a pasta do jogo primeiro!")
            return

        if not messagebox.askyesno("Restaurar Inglês",
            "Isso vai restaurar os arquivos originais em inglês a partir dos backups (.bak).\n\n"
            "O cache de tradução não será modificado.\n\n"
            "Tem certeza?"):
            return

        self.show_view("log")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", "=== RESTAURANDO INGLÊS ===\n\n")
        threading.Thread(target=self._do_restore, args=(game_path,), daemon=True).start()

    def _do_restore(self, game_path):
        redir = RedirectText(self.log_textbox)
        restored = 0
        for root, dirs, files in os.walk(game_path):
            for fname in files:
                if not fname.endswith(".bak"):
                    continue
                bak  = os.path.join(root, fname)
                orig = bak[:-4]
                if os.path.exists(orig):
                    shutil.copy2(bak, orig)
                    rel = os.path.relpath(orig, game_path)
                    redir.write(f"  ↩️  {rel}\n")
                    restored += 1
        redir.write(f"\n✅  {restored} arquivo(s) restaurados para inglês.\n")


if __name__ == "__main__":
    app = App()
    app.mainloop()
