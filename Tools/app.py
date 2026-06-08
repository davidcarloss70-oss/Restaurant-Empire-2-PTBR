import customtkinter as ctk
import json
import os
import threading
import sys
import io

# Optional: Add tools directory to path if needed to import scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setting appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class RedirectText(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert("end", string)
        self.text_widget.see("end")
        
    def flush(self):
        pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RE2 PT-BR Modding Tool")
        self.geometry("900x600")

        self.cache_path = "translation_cache.json"
        self.cache_data = {}
        self.filtered_keys = []
        self.current_page = 0
        self.items_per_page = 50

        # Create Layout (Grid)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Sidebar (Left)
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="RE2 Tradutor", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.editor_button = ctk.CTkButton(self.sidebar_frame, text="Editor", command=self.show_editor)
        self.editor_button.grid(row=1, column=0, padx=20, pady=10)

        self.log_button = ctk.CTkButton(self.sidebar_frame, text="Console Log", command=self.show_log)
        self.log_button.grid(row=2, column=0, padx=20, pady=10)

        self.apply_button = ctk.CTkButton(self.sidebar_frame, text="Aplicar Patch!", fg_color="#28a745", hover_color="#218838", font=ctk.CTkFont(weight="bold"), command=self.apply_patch)
        self.apply_button.grid(row=5, column=0, padx=20, pady=20)

        # 2. Main Area (Right)
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Editor View
        self.editor_view = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.editor_view.grid(row=0, column=0, sticky="nsew")
        self.editor_view.grid_rowconfigure(1, weight=1)
        self.editor_view.grid_columnconfigure(0, weight=1)
        
        # Search Bar
        self.search_frame = ctk.CTkFrame(self.editor_view, fg_color="transparent")
        self.search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Pesquisar texto original ou traduzido...")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)

        # List Frame
        self.list_frame = ctk.CTkScrollableFrame(self.editor_view, corner_radius=10)
        self.list_frame.grid(row=1, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Editor Edit Box (Bottom)
        self.edit_frame = ctk.CTkFrame(self.editor_view, corner_radius=10)
        self.edit_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.edit_frame.grid_columnconfigure(0, weight=1)
        
        self.lbl_editing = ctk.CTkLabel(self.edit_frame, text="Selecione um texto acima para editar", text_color="gray")
        self.lbl_editing.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.txt_edit = ctk.CTkTextbox(self.edit_frame, height=60)
        self.txt_edit.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.btn_save = ctk.CTkButton(self.edit_frame, text="Salvar Tradução", command=self.save_translation, state="disabled")
        self.btn_save.grid(row=2, column=0, sticky="e", padx=10, pady=10)

        # Log View
        self.log_view = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.log_view.grid_rowconfigure(0, weight=1)
        self.log_view.grid_columnconfigure(0, weight=1)
        
        self.log_textbox = ctk.CTkTextbox(self.log_view, state="normal")
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

        # Variables
        self.selected_key = None
        self.item_widgets = []

        self.load_cache()
        self.show_editor()

    def load_cache(self):
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self.cache_data = json.load(f)
            self.filtered_keys = list(self.cache_data.keys())
            self.render_list()
        except Exception as e:
            self.lbl_editing.configure(text=f"Erro ao carregar cache: {e}", text_color="red")

    def on_search(self, event):
        query = self.search_entry.get().lower()
        if not query:
            self.filtered_keys = list(self.cache_data.keys())
        else:
            self.filtered_keys = [k for k in self.cache_data.keys() 
                                  if query in k.lower() or (self.cache_data[k] and query in self.cache_data[k].lower())]
        self.render_list()

    def render_list(self):
        # Clear existing
        for widget in self.item_widgets:
            widget.destroy()
        self.item_widgets.clear()

        # Render first 100 max to avoid lag
        keys_to_render = self.filtered_keys[:100]
        
        if not keys_to_render:
            lbl = ctk.CTkLabel(self.list_frame, text="Nenhum resultado encontrado.", text_color="gray")
            lbl.grid(row=0, column=0, pady=20)
            self.item_widgets.append(lbl)
            return

        for i, key in enumerate(keys_to_render):
            val = self.cache_data[key]
            if not val: val = "[Não traduzido]"
            
            # Create a frame for each row
            row_frame = ctk.CTkFrame(self.list_frame, fg_color=("gray80", "gray20"), corner_radius=5)
            row_frame.grid(row=i, column=0, sticky="ew", pady=2, padx=5)
            row_frame.grid_columnconfigure(1, weight=1)

            # Bind click event
            row_frame.bind("<Button-1>", lambda e, k=key: self.select_item(k))

            lbl_orig = ctk.CTkLabel(row_frame, text=f"EN: {key[:50]}...", text_color="gray", justify="left")
            lbl_orig.grid(row=0, column=0, sticky="w", padx=10, pady=2)
            lbl_orig.bind("<Button-1>", lambda e, k=key: self.select_item(k))

            lbl_pt = ctk.CTkLabel(row_frame, text=f"PT: {val[:80]}...", justify="left", font=ctk.CTkFont(weight="bold"))
            lbl_pt.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 5))
            lbl_pt.bind("<Button-1>", lambda e, k=key: self.select_item(k))

            self.item_widgets.append(row_frame)

    def select_item(self, key):
        self.selected_key = key
        self.lbl_editing.configure(text=f"Editando: {key}", text_color="white")
        self.txt_edit.delete("1.0", "end")
        val = self.cache_data.get(key, "")
        if val:
            self.txt_edit.insert("1.0", val)
        self.btn_save.configure(state="normal")

    def save_translation(self):
        if not self.selected_key: return
        new_val = self.txt_edit.get("1.0", "end").strip()
        self.cache_data[self.selected_key] = new_val
        
        # Save to disk
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            self.lbl_editing.configure(text="Salvo com sucesso!", text_color="#28a745")
            self.render_list() # refresh list
        except Exception as e:
            self.lbl_editing.configure(text=f"Erro ao salvar: {e}", text_color="red")

    def show_editor(self):
        self.log_view.grid_forget()
        self.editor_view.grid(row=0, column=0, sticky="nsew")

    def show_log(self):
        self.editor_view.grid_forget()
        self.log_view.grid(row=0, column=0, sticky="nsew")

    def apply_patch(self):
        self.show_log()
        self.apply_button.configure(state="disabled", text="Aplicando...")
        self.log_textbox.insert("end", "=== Iniciando Injeção do Patch ===\n")
        
        # Redirect stdout
        sys.stdout = RedirectText(self.log_textbox)
        
        # Run in thread
        threading.Thread(target=self._run_scripts, daemon=True).start()

    def _run_scripts(self):
        try:
            import translate_all_safe
            import translate_std_set
            import translate_tutorials
            
            print("\n>> Executando translate_all_safe.py...")
            translate_all_safe.translate_all_safe()
            
            print("\n>> Executando translate_std_set.py...")
            translate_std_set.translate_std_set()
            
            print("\n>> Executando translate_tutorials.py...")
            translate_tutorials.translate_tutorials()
            
            print("\n=== PATCH APLICADO COM SUCESSO! ===")
        except Exception as e:
            print(f"\nERRO: {str(e)}")
        finally:
            sys.stdout = sys.__stdout__
            self.after(0, lambda: self.apply_button.configure(state="normal", text="Aplicar Patch!"))

if __name__ == "__main__":
    app = App()
    app.mainloop()
