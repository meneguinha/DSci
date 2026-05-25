import os
import sys
import json
import threading
import webbrowser
import tempfile
import html
import re
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_writable_path(filename):
    """Get path to a writable file/folder, located in the executable directory or fallback to home folder."""
    if getattr(sys, 'frozen', False):
        # Path of the executable
        exec_dir = os.path.dirname(os.path.abspath(sys.executable))
        # Check if we have write access to the executable directory
        if os.access(exec_dir, os.W_OK):
            return os.path.join(exec_dir, filename)
        else:
            # Fallback to User Home directory (e.g. ~/DSci/filename)
            home_dir = os.path.join(os.path.expanduser("~"), "DSci")
            os.makedirs(home_dir, exist_ok=True)
            return os.path.join(home_dir, filename)
    else:
        # Development mode
        dev_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dev_dir, filename)

# Project imports
import search_engine
import downloader
import ai_analyzer

# =====================================================================
# TITLE CLEANING AND FORMATTING HELPER
# =====================================================================
def clean_title(t):
    if not t:
        return ""
    # 1. Unescape HTML entities
    t = html.unescape(t)
    # 2. Strip HTML tags
    t = re.sub(r'<[^>]+>', '', t)
    # 3. Collapse whitespaces
    t = " ".join(t.split())
    # 4. Handle all-caps titles
    if t.isupper() and len(t.split()) > 3:
        # Capitalize the first letter and keep the rest lowercase
        t = t.capitalize()
    return t


# =====================================================================
# MODERN TOOLTIP WIDGET
# =====================================================================
class ToolTip:
    def __init__(self, widget, text, delay=1500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.id = None
        
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        
    def enter(self, event=None):
        self.schedule()
        
    def leave(self, event=None):
        self.unschedule()
        self.hide_tip()
        
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show_tip)
        
    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)
            
    def show_tip(self):
        if self.tip_window or not self.text:
            return
            
        x = self.widget.winfo_pointerx() + 10
        y = self.widget.winfo_pointery() + 15
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Style tooltips to match modern light/dark theme
        appearance = ctk.get_appearance_mode()
        if appearance == "Dark":
            bg = "#1E293B"      # Deep slate navy
            fg = "#F8FAFC"      # Soft white
            border_color = "#334155" # Subtle border
        else:
            bg = "#F8FAFC"      # Soft slate white
            fg = "#0F172A"      # Deep charcoal
            border_color = "#E2E8F0" # Soft gray border
            
        # Create a frame to act as a border container
        border_frame = tk.Frame(
            tw,
            background=border_color,
            padx=1,
            pady=1
        )
        border_frame.pack()
        
        label = tk.Label(
            border_frame,
            text=self.text,
            justify="left",
            background=bg,
            foreground=fg,
            font=("Segoe UI", 10),
            padx=10,
            pady=6,
            wraplength=350
        )
        label.pack()
        
    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


# =====================================================================
# FILE OVERWRITE / CONFLICT RESOLUTION DIALOG
# =====================================================================
class ConflictDialog(ctk.CTkToplevel):
    def __init__(self, parent, filename):
        super().__init__(parent)
        self.title("DSci - Conflito de Arquivo")
        self.geometry("660x220")
        self.resizable(False, False)
        
        # Make the dialog modal
        self.transient(parent)
        self.grab_set()
        
        self.result = None # Choice: 'replace', 'replace_all', 'rename', 'rename_all', 'cancel'
        
        # Visual Header
        self.header_label = ctk.CTkLabel(
            self,
            text="⚠️ Conflito de Arquivo",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_WARNING if 'COLOR_WARNING' in globals() else "orange"
        )
        self.header_label.pack(pady=(15, 5), padx=20, anchor="w")
        
        # Message
        message_text = (
            f"O arquivo a seguir já existe na pasta de downloads:\n"
            f"  \"{filename}\"\n\n"
            f"Como deseja proceder?"
        )
        self.msg_label = ctk.CTkLabel(
            self,
            text=message_text,
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.msg_label.pack(pady=5, padx=20, fill="x", anchor="w")
        
        # Button frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(15, 15), padx=20, fill="x")
        
        # Grid config
        for col in range(5):
            btn_frame.grid_columnconfigure(col, weight=1)
            
        # Get colors or fallback to defaults
        primary_color = COLOR_PRIMARY if 'COLOR_PRIMARY' in globals() else "#4F46E5"
        primary_hover = COLOR_PRIMARY_HOVER if 'COLOR_PRIMARY_HOVER' in globals() else "#4338CA"
        secondary_color = COLOR_SECONDARY if 'COLOR_SECONDARY' in globals() else "#0D9488"
        secondary_hover = COLOR_SECONDARY_HOVER if 'COLOR_SECONDARY_HOVER' in globals() else "#0F766E"
        danger_color = COLOR_DANGER if 'COLOR_DANGER' in globals() else "#DC2626"
        danger_hover = COLOR_DANGER_HOVER if 'COLOR_DANGER_HOVER' in globals() else "#B91C1C"
        
        # Buttons
        self.btn_replace = ctk.CTkButton(
            btn_frame,
            text="Substituir",
            fg_color=primary_color,
            hover_color=primary_hover,
            text_color="white",
            width=90,
            command=lambda: self.set_result("replace")
        )
        self.btn_replace.grid(row=0, column=0, padx=4)
        
        self.btn_replace_all = ctk.CTkButton(
            btn_frame,
            text="Substituir Todos",
            fg_color=primary_color,
            hover_color=primary_hover,
            text_color="white",
            width=110,
            command=lambda: self.set_result("replace_all")
        )
        self.btn_replace_all.grid(row=0, column=1, padx=4)
        
        self.btn_rename = ctk.CTkButton(
            btn_frame,
            text="Salvar como Novo",
            fg_color=secondary_color,
            hover_color=secondary_hover,
            text_color="white",
            width=110,
            command=lambda: self.set_result("rename")
        )
        self.btn_rename.grid(row=0, column=2, padx=4)
        
        self.btn_rename_all = ctk.CTkButton(
            btn_frame,
            text="Salvar todos como Novos",
            fg_color=secondary_color,
            hover_color=secondary_hover,
            text_color="white",
            width=140,
            command=lambda: self.set_result("rename_all")
        )
        self.btn_rename_all.grid(row=0, column=3, padx=4)
        
        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            fg_color=danger_color,
            hover_color=danger_hover,
            text_color="white",
            width=80,
            command=lambda: self.set_result("cancel")
        )
        self.btn_cancel.grid(row=0, column=4, padx=4)
        
        # Bind close event to cancel
        self.protocol("WM_DELETE_WINDOW", lambda: self.set_result("cancel"))
        
        # Center window
        self.center_window(parent)
        
    def set_result(self, res):
        self.result = res
        self.destroy()
        
    def center_window(self, parent):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        parent_top = parent.winfo_toplevel()
        x = parent_top.winfo_x() + (parent_top.winfo_width() // 2) - (width // 2)
        y = parent_top.winfo_y() + (parent_top.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")


# =====================================================================
# DESIGN SYSTEM - HARMONIOUS COLOR TOKENS (Light Mode / Dark Mode)
# =====================================================================
BG_MAIN = ("#F8FAFC", "#0F172A")          # Soft slate white / Deep slate navy
BG_SIDEBAR = ("#F1F5F9", "#1E293B")       # Light slate gray / Slate navy
BG_CARD = ("#FFFFFF", "#1E293B")          # Pure white / Slate navy
BG_CARD_ROW = ("#FFFFFF", "#1E293B")      # Pure white / Slate navy for inner list rows (draws as cards)
BG_ROW_HOVER = ("#F1F5F9", "#334155")     # Hover highlights for buttons/rows
BORDER_COLOR = ("#E2E8F0", "#334155")     # Soft gray borders / Slate borders

# Text Colors
TEXT_PRIMARY = ("#0F172A", "#F8FAFC")     # Deep charcoal / Soft white
TEXT_MUTED = ("#64748B", "#94A3B8")       # Slate gray / Light slate gray

# Accent Actions (Light / Dark)
COLOR_PRIMARY = ("#4F46E5", "#6366F1")    # Indigo (Primary Brand Accent)
COLOR_PRIMARY_HOVER = ("#4338CA", "#4F46E5")
COLOR_SECONDARY = ("#0D9488", "#14B8A6")  # Teal (for downloads)
COLOR_SECONDARY_HOVER = ("#0F766E", "#0D9488")
COLOR_PURPLE = ("#7C3AED", "#8B5CF6")     # Purple (for AI)
COLOR_PURPLE_HOVER = ("#6D28D9", "#7C3AED")
COLOR_DANGER = ("#DC2626", "#EF4444")     # Red (for Stop/Cancel)
COLOR_DANGER_HOVER = ("#B91C1C", "#DC2626")

# Status badges
COLOR_SUCCESS = ("#16A34A", "#22C55E")    # Green
COLOR_WARNING = ("#EA580C", "#F97316")    # Orange
COLOR_INFO = ("#0284C7", "#38BDF8")       # Light Blue

# Clickable Links
COLOR_LINK_DOI = ("#1D4ED8", "#60A5FA")   # Royal Blue / Light Blue
COLOR_LINK_PDF = ("#0F766E", "#2DD4BF")   # Deep Teal / Light Teal

# =====================================================================


class PaperRowFrame(ctk.CTkFrame):
    """A custom widget to display a single academic paper with checkbox, metadata, and link."""
    def __init__(self, master, paper, on_toggle_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.paper = paper
        
        # Grid layout: Checkbox (col 0), Content (col 1), Database Badge (col 2)
        self.grid_columnconfigure(1, weight=1)
        
        # Checkbox
        self.var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            self, 
            text="", 
            variable=self.var, 
            width=24,
            command=on_toggle_callback,
            border_color=BORDER_COLOR,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER
        )
        self.checkbox.grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")
        
        # Content frame (Title, Authors, Source, DOI)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, padx=5, pady=10, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Title Label (wrapped and bold)
        title_text = paper.get("title", "Untitled Document")
        self.title_label = ctk.CTkLabel(
            self.content_frame, 
            text=title_text, 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=550
        )
        self.title_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        # Authors + Year + Source Label
        authors = paper.get("authors", "Unknown Author(s)")
        year = paper.get("year", "Unknown Year")
        source = paper.get("source", "Unknown Source")
        meta_text = f"Autores: {authors}\nAno: {year} | Fonte: {source}"
        
        self.meta_label = ctk.CTkLabel(
            self.content_frame, 
            text=meta_text, 
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=550
        )
        self.meta_label.grid(row=1, column=0, sticky="w", pady=(0, 5))
        
        # DOI link / URL Indicator
        doi = paper.get("doi")
        pdf_url = paper.get("pdf_url")
        
        links_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        links_frame.grid(row=2, column=0, sticky="w")
        
        col_idx = 0
        if doi:
            doi_url = f"https://doi.org/{doi}"
            doi_btn = ctk.CTkButton(
                links_frame,
                text=f"DOI: {doi}",
                font=ctk.CTkFont(size=11, underline=True),
                text_color=COLOR_LINK_DOI,
                fg_color="transparent",
                hover_color=BG_ROW_HOVER,
                height=16,
                width=50,
                anchor="w",
                command=lambda url=doi_url: webbrowser.open(url)
            )
            doi_btn.grid(row=0, column=col_idx, padx=(0, 10), sticky="w")
            col_idx += 1
            
        if pdf_url:
            pdf_btn = ctk.CTkButton(
                links_frame,
                text="🔗 Ver PDF Original",
                font=ctk.CTkFont(size=11, underline=True),
                text_color=COLOR_LINK_PDF,
                fg_color="transparent",
                hover_color=BG_ROW_HOVER,
                height=16,
                width=50,
                anchor="w",
                command=self.open_pdf
            )
            pdf_btn.grid(row=0, column=col_idx, padx=(0, 10), sticky="w")
            col_idx += 1

        # Button to toggle abstract
        self.abstract_visible = False
        self.abstract_label = None
        self.abstract_text = paper.get("abstract") or "Resumo não disponível."
        
        self.toggle_abstract_btn = ctk.CTkButton(
            links_frame,
            text="📄 Ver Resumo",
            font=ctk.CTkFont(size=11, underline=True),
            text_color=COLOR_PRIMARY,
            fg_color="transparent",
            hover_color=BG_ROW_HOVER,
            height=16,
            width=80,
            anchor="w",
            command=self.toggle_abstract
        )
        self.toggle_abstract_btn.grid(row=0, column=col_idx, sticky="w")
            
        # Database Badge
        db_source = paper.get("database", "API")
        badge_color = COLOR_PRIMARY
        if "Crossref" in db_source and "OpenAlex" in db_source:
            badge_color = COLOR_PURPLE
        elif "Crossref" in db_source:
            badge_color = COLOR_INFO
        elif "OpenAlex" in db_source:
            badge_color = COLOR_SECONDARY
            
        self.badge = ctk.CTkLabel(
            self,
            text=db_source,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="white",
            fg_color=badge_color,
            corner_radius=6,
            padx=8,
            pady=4
        )
        self.badge.grid(row=0, column=2, padx=15, pady=10, sticky="e")

    def is_selected(self):
        return self.var.get()

    def set_selected(self, val):
        self.var.set(val)
        if val:
            self.checkbox.select()
        else:
            self.checkbox.deselect()

    def toggle_abstract(self):
        if self.abstract_visible:
            if self.abstract_label:
                self.abstract_label.grid_forget()
            self.toggle_abstract_btn.configure(text="📄 Ver Resumo")
            self.abstract_visible = False
        else:
            if not self.abstract_label:
                self.abstract_label = ctk.CTkLabel(
                    self.content_frame,
                    text=self.abstract_text,
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color=TEXT_MUTED,
                    anchor="w",
                    justify="left",
                    wraplength=550
                )
            self.abstract_label.grid(row=3, column=0, sticky="w", pady=(5, 0))
            self.toggle_abstract_btn.configure(text="📄 Ocultar Resumo")
            self.abstract_visible = True

    def open_pdf(self):
        pdf_url = self.paper.get("pdf_url")
        title = self.paper.get("title", "Untitled")
        year = self.paper.get("year", "ano_desconhecido")
        
        downloads_dir = get_writable_path("downloads")
        safe_title = downloader.sanitize_filename(title)
        pdf_filename = f"{safe_title} ({year}).pdf"
        pdf_path = os.path.join(downloads_dir, pdf_filename)
        
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
                return
            except Exception as e:
                pass
                
        if pdf_url:
            webbrowser.open(pdf_url)
        else:
            messagebox.showwarning("Aviso", "Nenhum link ou arquivo PDF disponível para este artigo.")


class AIPaperRowFrame(ctk.CTkFrame):
    """List item representing a paper in the AI Analysis tab."""
    def __init__(self, master, paper, click_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.paper = paper
        self.click_callback = click_callback
        
        self.grid_columnconfigure(0, weight=1)
        
        # Clickable button for paper selection
        title = paper.get("title", "Untitled Document")
        
        # Word wrap the title into up to 2 lines for better sidebar visibility
        def wrap_title(t, max_len=55, wrap_threshold=35):
            # If the title is short enough, do not wrap it at all
            if len(t) <= wrap_threshold:
                return t
                
            # If the title is within the max_len limit, try to wrap it in the middle
            if len(t) <= max_len:
                mid = len(t) // 2
                for i in range(len(t) // 2):
                    if mid - i > 0 and t[mid - i] == " ":
                        return t[:mid - i] + "\n" + t[mid - i + 1:]
                    if mid + i < len(t) and t[mid + i] == " ":
                        return t[:mid + i] + "\n" + t[mid + i + 1:]
                return t
                
            # If the title is longer than max_len, truncate and add ellipsis, then wrap
            truncated = t[:max_len - 3].strip() + "..."
            mid = len(truncated) // 2
            for i in range(len(truncated) // 2):
                if mid - i > 0 and truncated[mid - i] == " ":
                    return truncated[:mid - i] + "\n" + truncated[mid - i + 1:]
                if mid + i < len(truncated) and truncated[mid + i] == " ":
                    return truncated[:mid + i] + "\n" + truncated[mid + i + 1:]
            return truncated[:mid] + "\n" + truncated[mid:]

        display_title = wrap_title(title)
            
        self.btn = ctk.CTkButton(
            self,
            text=display_title,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=TEXT_PRIMARY,
            anchor="w",
            hover_color=BG_ROW_HOVER,
            command=self.on_click
        )
        self.btn.grid(row=0, column=0, sticky="ew", padx=(5, 0), pady=5)
        
        # Configure internal label to align text to the left
        try:
            self.btn._text_label.configure(justify="left", anchor="w")
        except Exception:
            pass
            
        # Disable keyboard focus on the underlying Tkinter canvas to prevent layout shifts
        try:
            self.btn._canvas.configure(takefocus=0)
        except Exception:
            pass
        
        # Status badge
        self.status = "Pendente"
        self.status_badge = ctk.CTkLabel(
            self,
            text=self.status,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=TEXT_MUTED,
            text_color="white",
            corner_radius=4,
            padx=6,
            pady=3
        )
        self.status_badge.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        # Bind double click to open PDF locally
        self.btn.bind("<Double-Button-1>", self.on_double_click)
        self.bind("<Double-Button-1>", self.on_double_click)
        self.status_badge.bind("<Double-Button-1>", self.on_double_click)
        
        # Attach Tooltips with full clean title, delay 1.5s (1500 ms)
        ToolTip(self.btn, title, delay=1500)
        ToolTip(self.status_badge, title, delay=1500)
        ToolTip(self, title, delay=1500)
        
    def on_click(self):
        self.click_callback(self.paper)
        
    def on_double_click(self, event=None):
        title = self.paper.get("title", "Untitled")
        year = self.paper.get("year", "ano_desconhecido")
        safe_title = downloader.sanitize_filename(title)
        pdf_filename = f"{safe_title} ({year}).pdf"
        
        downloads_dir = get_writable_path("downloads")
        pdf_path = os.path.join(downloads_dir, pdf_filename)
        
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir o arquivo PDF: {e}")
        else:
            messagebox.showwarning(
                "Arquivo não encontrado", 
                f"O arquivo PDF deste artigo ainda não foi baixado na pasta downloads.\n\nNome esperado: {pdf_filename}"
            )
        return "break"
        
    def update_status(self, new_status, color=None):
        self.status = new_status
        self.status_badge.configure(text=new_status)
        if color:
            if isinstance(color, tuple):
                self.status_badge.configure(fg_color=color)
            else:
                self.status_badge.configure(fg_color=color)


class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Buscador, Downloader & Analisador de Artigos Científicos")
        self.geometry("1200x800")
        self.minsize(1050, 750)
        
        # Configure global window background color
        self.configure(fg_color=BG_MAIN)
        
        # Standard variables
        self.results = []
        self.row_widgets = []
        
        # AI Specific variables
        self.ai_row_widgets = []
        self.selected_ai_paper = None
        self.ai_running = False
        self.ai_analysis_cancelled = False
        
        # Set default appearance to Light Theme!
        ctk.set_appearance_mode("Light")
        theme_path = get_resource_path("papertools_theme.json")
        if os.path.exists(theme_path):
            ctk.set_default_color_theme(theme_path)
        else:
            ctk.set_default_color_theme("blue")
        
        # Create Layout
        self.setup_layout()
        
        # Ensure downloads folder exists in project directory
        self.project_dir = get_writable_path("")
        self.downloads_dir = get_writable_path("downloads")
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        # Load API configurations
        self.load_settings()
        
    def setup_layout(self):
        # Configure grid weight: sidebar (col 0, weight 0), main (col 1, weight 1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ================= SIDEBAR PANEL =================
        self.sidebar = ctk.CTkFrame(
            self, 
            width=280, 
            corner_radius=0, 
            fg_color=BG_SIDEBAR, 
            border_width=1, 
            border_color=BORDER_COLOR
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(11, weight=1) # Push version/credits to bottom
        self.sidebar.grid_columnconfigure(0, weight=1)
        
        # Sidebar Header Frame (Logo + Collapse Button)
        self.sidebar_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_header.grid(row=0, column=0, padx=15, pady=(20, 20), sticky="ew")
        self.sidebar_header.grid_columnconfigure(0, weight=1)
        
        self.logo_label = ctk.CTkLabel(
            self.sidebar_header, 
            text="📚 DSci", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.logo_label.grid(row=0, column=0, sticky="w")
        
        self.collapse_btn = ctk.CTkButton(
            self.sidebar_header,
            text="◀",
            width=28,
            height=28,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=BG_ROW_HOVER,
            command=self.toggle_sidebar
        )
        self.collapse_btn.grid(row=0, column=1, sticky="e")
        
        # Search Keyword Input
        self.keyword_label = ctk.CTkLabel(self.sidebar, text="Palavra-chave / Assunto:", text_color=TEXT_PRIMARY, anchor="w")
        self.keyword_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.keyword_entry = ctk.CTkEntry(
            self.sidebar, 
            placeholder_text="Ex: machine learning, covid-19",
            width=240,
            fg_color=("white", "#1E293B"),
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            border_color=BORDER_COLOR
        )
        self.keyword_entry.grid(row=2, column=0, padx=20, pady=(0, 10))
        self.keyword_entry.bind("<Return>", lambda e: self.start_search())
        
        # Max Results Input
        self.limit_label = ctk.CTkLabel(self.sidebar, text="Limite Máximo de Artigos:", text_color=TEXT_PRIMARY, anchor="w")
        self.limit_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.limit_entry = ctk.CTkEntry(
            self.sidebar, 
            width=240,
            fg_color=("white", "#1E293B"),
            text_color=TEXT_PRIMARY,
            border_color=BORDER_COLOR
        )
        self.limit_entry.insert(0, "20") # Default value
        self.limit_entry.grid(row=4, column=0, padx=20, pady=(0, 10))
        
        # Language Selection
        self.lang_label = ctk.CTkLabel(self.sidebar, text="Idioma do Artigo:", text_color=TEXT_PRIMARY, anchor="w")
        self.lang_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")
        self.lang_optionemenu = ctk.CTkOptionMenu(
            self.sidebar, 
            values=["Qualquer", "Inglês", "Português"],
            width=240,
            fg_color=COLOR_PRIMARY,
            button_color=COLOR_PRIMARY,
            button_hover_color=COLOR_PRIMARY_HOVER,
            text_color="white"
        )
        self.lang_optionemenu.grid(row=6, column=0, padx=20, pady=(0, 10))
        
        # Email (for polite API usage)
        self.email_label = ctk.CTkLabel(
            self.sidebar, 
            text="E-mail (opcional, para APIs):", 
            anchor="w",
            text_color=TEXT_MUTED
        )
        self.email_label.grid(row=7, column=0, padx=20, pady=(10, 0), sticky="w")
        self.email_entry = ctk.CTkEntry(
            self.sidebar, 
            placeholder_text="seu_email@exemplo.com", 
            width=240,
            fg_color=("white", "#1E293B"),
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            border_color=BORDER_COLOR
        )
        self.email_entry.grid(row=8, column=0, padx=20, pady=(0, 10))
        
        # Search Button
        self.search_btn = ctk.CTkButton(
            self.sidebar, 
            text="Pesquisar Artigos", 
            command=self.start_search,
            font=ctk.CTkFont(weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="white",
            height=35
        )
        self.search_btn.grid(row=9, column=0, padx=20, pady=20)
        
        # Theme/Appearance selector (Default set to Light)
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar, text="Modo de Aparência:", text_color=TEXT_PRIMARY, anchor="w")
        self.appearance_mode_label.grid(row=10, column=0, padx=20, pady=(10, 0), sticky="w")
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(
            self.sidebar, 
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode,
            fg_color=BG_ROW_HOVER,
            button_color=BG_ROW_HOVER,
            button_hover_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.appearance_mode_optionemenu.set("Light")
        self.appearance_mode_optionemenu.grid(row=11, column=0, padx=20, pady=(0, 20), sticky="s")
        
        # ================= MAIN CONTAINER PANEL =================
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0) # Collapsed top bar (normally hidden)
        self.main_frame.grid_rowconfigure(1, weight=1) # Tabview takes all space
        self.main_frame.grid_rowconfigure(2, weight=0) # Progress frame takes minimal space
        
        # Collapsed Header Top Bar (initially hidden)
        self.top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_bar.grid_columnconfigure(1, weight=1)
        
        self.expand_btn = ctk.CTkButton(
            self.top_bar,
            text="▶",
            width=28,
            height=28,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=BG_ROW_HOVER,
            command=self.toggle_sidebar
        )
        self.expand_btn.grid(row=0, column=0, padx=(0, 10), sticky="w")
        
        self.top_bar_title = ctk.CTkLabel(
            self.top_bar,
            text="📚 DSci",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.top_bar_title.grid(row=0, column=1, sticky="w")
        
        # CTkTabview Container
        self.tabview = ctk.CTkTabview(
            self.main_frame,
            fg_color=BG_CARD,
            segmented_button_selected_color=COLOR_PRIMARY,
            segmented_button_selected_hover_color=COLOR_PRIMARY_HOVER,
            segmented_button_unselected_hover_color=BG_ROW_HOVER,
            text_color=TEXT_PRIMARY,
            border_width=1,
            border_color=BORDER_COLOR,
            command=self.on_tab_changed
        )
        self.tabview.grid(row=1, column=0, sticky="nsew")
        
        # Create Tabs
        self.tab_search = self.tabview.add("Busca & Downloads")
        self.tab_ai = self.tabview.add("Análise por IA")
        
        # Configure Tab 1 (Search)
        self.tab_search.grid_columnconfigure(0, weight=1)
        self.tab_search.grid_rowconfigure(1, weight=1) # Scrollable Frame takes vertical space
        
        # Configure Tab 2 (AI Analysis)
        self.tab_ai.grid_columnconfigure(0, weight=1)
        self.tab_ai.grid_rowconfigure(1, weight=1) # Split result view takes ALL remaining vertical space
        
        # ================= TAB 1: SEARCH & DOWNLOADS =================
        
        # Top Header of Main Area (Tab 1)
        self.header_frame = ctk.CTkFrame(self.tab_search, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.results_title = ctk.CTkLabel(
            self.header_frame, 
            text="Resultados da Pesquisa", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.results_title.grid(row=0, column=0, sticky="w")
        
        # Bulk Select controls
        self.select_controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.select_controls_frame.grid(row=0, column=2, sticky="e")
        
        self.select_all_btn = ctk.CTkButton(
            self.select_controls_frame,
            text="Selecionar Todos",
            width=110,
            height=25,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            hover_color=BG_ROW_HOVER,
            command=self.select_all_action
        )
        self.select_all_btn.grid(row=0, column=0, padx=5)
        
        self.deselect_all_btn = ctk.CTkButton(
            self.select_controls_frame,
            text="Desmarcar Todos",
            width=110,
            height=25,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            hover_color=BG_ROW_HOVER,
            command=self.deselect_all_action
        )
        self.deselect_all_btn.grid(row=0, column=1, padx=5)
        
        # Scrollable Frame for listing search results
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.tab_search, 
            label_text="Artigos Encontrados",
            fg_color=BG_MAIN,
            label_text_color=TEXT_PRIMARY
        )
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # Empty placeholder inside scrollable frame
        self.placeholder_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="Insira uma palavra-chave e clique em 'Pesquisar' para listar artigos de livre acesso.",
            font=ctk.CTkFont(size=13, slant="italic"),
            text_color=TEXT_MUTED,
            pady=100
        )
        self.placeholder_label.grid(row=0, column=0, sticky="nsew")
        
        # Bottom controls for Tab 1 (Selection counter, Download Button)
        self.dl_controls = ctk.CTkFrame(self.tab_search, fg_color="transparent")
        self.dl_controls.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        self.dl_controls.grid_columnconfigure(0, weight=1)
        
        self.counter_label = ctk.CTkLabel(
            self.dl_controls, 
            text="Artigos selecionados: 0 / 0", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.counter_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.download_btn = ctk.CTkButton(
            self.dl_controls,
            text="⬇️ Baixar Artigos (Pasta Downloads)",
            font=ctk.CTkFont(weight="bold"),
            command=self.start_download,
            state="disabled",
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color="white"
        )
        self.download_btn.grid(row=0, column=1, padx=15, pady=10, sticky="e")
        
        # Log Console (Only displayed inside tab_search to save vertical space)
        self.log_textbox = ctk.CTkTextbox(
            self.tab_search,
            height=90,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=("white", "#0F172A"),
            text_color=TEXT_PRIMARY,
            border_width=1,
            border_color=BORDER_COLOR,
            state="disabled"
        )
        self.log_textbox.grid(row=3, column=0, padx=10, pady=(10, 0), sticky="ew")
        
        # ================= TAB 2: AI ANALYSIS PANEL =================
        
        # Side-by-side Top AI Controls Frame (API Config on left, Prompt on right)
        self.top_ai_controls = ctk.CTkFrame(self.tab_ai, fg_color="transparent")
        self.top_ai_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.top_ai_controls.grid_columnconfigure(0, weight=2) # API Config (left, 40%)
        self.top_ai_controls.grid_columnconfigure(1, weight=3) # Prompt Config (right, 60%)
        
        # 1. API Configuration Panel (Stacked vertically to save width)
        self.api_config_frame = ctk.CTkFrame(self.top_ai_controls, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        self.api_config_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        self.api_config_frame.grid_columnconfigure(0, weight=1)
        
        # Base URL
        ctk.CTkLabel(
            self.api_config_frame, 
            text="URL Base da API (OpenAI-compatible):", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, padx=15, pady=(8, 0), sticky="w")
        self.api_url_entry = ctk.CTkEntry(
            self.api_config_frame, 
            height=24,
            fg_color=("white", "#1E293B"),
            text_color=TEXT_PRIMARY,
            border_color=BORDER_COLOR
        )
        self.api_url_entry.insert(0, "https://api.openai.com/v1")
        self.api_url_entry.grid(row=1, column=0, padx=15, pady=(2, 6), sticky="ew")
        
        # API Key
        key_label_frame = ctk.CTkFrame(self.api_config_frame, fg_color="transparent")
        key_label_frame.grid(row=2, column=0, padx=15, pady=0, sticky="ew")
        key_label_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            key_label_frame, 
            text="Chave de API (API Key):", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w")
        
        self.show_key_var = ctk.BooleanVar(value=False)
        self.show_key_cb = ctk.CTkCheckBox(
            key_label_frame, 
            text="Mostrar", 
            variable=self.show_key_var, 
            command=self.toggle_key_visibility,
            width=65,
            font=ctk.CTkFont(size=10),
            text_color=TEXT_PRIMARY,
            border_color=BORDER_COLOR,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER
        )
        self.show_key_cb.grid(row=0, column=1, sticky="e")
        
        self.api_key_entry = ctk.CTkEntry(
            self.api_config_frame, 
            show="*", 
            height=24,
            fg_color=("white", "#1E293B"),
            text_color=TEXT_PRIMARY,
            border_color=BORDER_COLOR
        )
        self.api_key_entry.grid(row=3, column=0, padx=15, pady=(2, 6), sticky="ew")
        
        # Model Name
        ctk.CTkLabel(
            self.api_config_frame, 
            text="Nome do Modelo (Model):", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_PRIMARY
        ).grid(row=4, column=0, padx=15, pady=0, sticky="w")
        self.api_model_entry = ctk.CTkEntry(
            self.api_config_frame, 
            height=24,
            fg_color=("white", "#1E293B"),
            text_color=TEXT_PRIMARY,
            border_color=BORDER_COLOR
        )
        self.api_model_entry.insert(0, "gpt-4o-mini")
        self.api_model_entry.grid(row=5, column=0, padx=15, pady=(2, 8), sticky="ew")
        
        self.save_config_btn = ctk.CTkButton(
            self.api_config_frame,
            text="💾 Salvar Configurações",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="white",
            height=24,
            command=self.save_settings
        )
        self.save_config_btn.grid(row=6, column=0, padx=15, pady=(2, 8), sticky="ew")
        
        # 2. Prompt Frame (Spans alongside API configurations)
        self.prompt_frame = ctk.CTkFrame(self.top_ai_controls, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        self.prompt_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        self.prompt_frame.grid_columnconfigure(0, weight=1)
        self.prompt_frame.grid_rowconfigure(1, weight=1) # Prompt textbox takes vertical space
        
        ctk.CTkLabel(
            self.prompt_frame, 
            text="Instruções / Prompt para Análise:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, padx=15, pady=(8, 0), sticky="w")
        
        self.prompt_textbox = ctk.CTkTextbox(
            self.prompt_frame, 
            height=95,
            fg_color=("white", "#0F172A"),
            text_color=TEXT_PRIMARY,
            border_width=1,
            border_color=BORDER_COLOR
        )
        self.prompt_textbox.insert(
            "1.0", 
            "Forneça um resumo executivo deste artigo científico, destacando:\n"
            "1. O problema de pesquisa e objetivo principal.\n"
            "2. A metodologia abordada.\n"
            "3. Os resultados e principais conclusões."
        )
        self.prompt_textbox.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        
        # Action Buttons frame (Analyze and Stop side-by-side)
        self.prompt_actions = ctk.CTkFrame(self.prompt_frame, fg_color="transparent")
        self.prompt_actions.grid(row=2, column=0, padx=15, pady=(0, 8), sticky="e")
        
        self.stop_btn = ctk.CTkButton(
            self.prompt_actions,
            text="🛑 Parar Análise",
            font=ctk.CTkFont(weight="bold"),
            fg_color="transparent",
            border_color=COLOR_DANGER,
            border_width=1.5,
            text_color=COLOR_DANGER,
            hover_color=("#FEE2E2", "#2D1A1A"), # Soft red background on hover
            height=28,
            state="disabled",
            command=self.cancel_ai_analysis
        )
        self.stop_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.analyze_btn = ctk.CTkButton(
            self.prompt_actions,
            text="🧠 Analisar Artigos Selecionados com IA",
            font=ctk.CTkFont(weight="bold"),
            fg_color=COLOR_PURPLE,
            hover_color=COLOR_PURPLE_HOVER,
            text_color="white",
            height=28,
            command=self.start_ai_analysis
        )
        self.analyze_btn.grid(row=0, column=1, padx=(5, 0))
        
        # 3. AI Results Split Layout (Wider right pane to maximize AI response area)
        self.ai_results_frame = ctk.CTkFrame(self.tab_ai, fg_color="transparent")
        self.ai_results_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.ai_results_frame.grid_columnconfigure(0, weight=3, uniform="ai_split") # Left List (30% width)
        self.ai_results_frame.grid_columnconfigure(1, weight=7, uniform="ai_split") # Right Response View (70% width)
        self.ai_results_frame.grid_rowconfigure(0, weight=1)
        
        # Left Scrollable Pane: Selected papers list
        self.ai_papers_scrollable = ctk.CTkScrollableFrame(
            self.ai_results_frame, 
            label_text="Documentos para Análise",
            fg_color=BG_MAIN,
            label_text_color=TEXT_PRIMARY
        )
        self.ai_papers_scrollable.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        self.ai_papers_scrollable.grid_columnconfigure(0, weight=1)
        
        self.ai_placeholder = ctk.CTkLabel(
            self.ai_papers_scrollable,
            text="Nenhum artigo selecionado para análise no momento.\nSelecione artigos na aba de busca e clique em 'Analisar'.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=TEXT_MUTED,
            pady=80
        )
        self.ai_placeholder.grid(row=0, column=0, sticky="nsew")
        
        # Right Pane: Detailed Response Panel (Enlarged Area)
        self.ai_detail_frame = ctk.CTkFrame(self.ai_results_frame, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        self.ai_detail_frame.grid(row=0, column=1, padx=(5, 0), sticky="nsew")
        self.ai_detail_frame.grid_columnconfigure(0, weight=1)
        self.ai_detail_frame.grid_rowconfigure(1, weight=1) # Textbox takes ALL vertical space
        
        self.ai_detail_title = ctk.CTkLabel(
            self.ai_detail_frame,
            text="Selecione um artigo ao lado para ver a resposta da IA",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=600 # Wrap text to prevent stretching columns
        )
        self.ai_detail_title.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.ai_response_textbox = ctk.CTkTextbox(
            self.ai_detail_frame,
            font=ctk.CTkFont(size=12),
            fg_color=("white", "#0F172A"),
            text_color=TEXT_PRIMARY,
            border_width=1,
            border_color=BORDER_COLOR,
            state="disabled"
        )
        self.ai_response_textbox.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="nsew")
        
        # Buttons underneath detailed response
        self.response_actions = ctk.CTkFrame(self.ai_detail_frame, fg_color="transparent")
        self.response_actions.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.response_actions.grid_columnconfigure(2, weight=1)
        
        self.copy_btn = ctk.CTkButton(
            self.response_actions,
            text="📋 Copiar Análise",
            width=120,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="white",
            command=self.copy_ai_response,
            state="disabled"
        )
        self.copy_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.save_txt_btn = ctk.CTkButton(
            self.response_actions,
            text="💾 Salvar (.txt)",
            width=120,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="white",
            command=self.save_ai_response,
            state="disabled"
        )
        self.save_txt_btn.grid(row=0, column=1, padx=5)
        
        # ================= SHARED BOTTOM LOGS & PROGRESS =================
        # Shared bottom progress frame outside tabs
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        self.progress_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="Status: Pronto",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED
        )
        self.status_label.grid(row=0, column=0, padx=15, pady=(5, 0), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, 
            height=8,
            fg_color=BG_ROW_HOVER,
            progress_color=COLOR_PRIMARY
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, padx=15, pady=(5, 10), sticky="ew")
        
        self.log("Console de logs inicializado.")

    # ================= SETTINGS FILE ACTIONS =================
    def load_settings(self):
        config_path = get_writable_path("config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.api_url_entry.delete(0, "end")
                    self.api_url_entry.insert(0, config.get("base_url", "https://api.openai.com/v1"))
                    
                    self.api_key_entry.delete(0, "end")
                    self.api_key_entry.insert(0, config.get("api_key", ""))
                    
                    self.api_model_entry.delete(0, "end")
                    self.api_model_entry.insert(0, config.get("model", "gpt-4o-mini"))
                    self.log("Configurações da API carregadas com sucesso.")
            except Exception as e:
                self.log(f"Erro ao carregar configurações: {e}")
                
    def save_settings(self):
        base_url = self.api_url_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        model = self.api_model_entry.get().strip()
        
        config = {
            "base_url": base_url,
            "api_key": api_key,
            "model": model
        }
        
        config_path = get_writable_path("config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            self.log("Configurações da API salvas com sucesso.")
            messagebox.showinfo("Sucesso", "Configurações da API salvas com sucesso!")
        except Exception as e:
            self.log(f"Erro ao salvar configurações: {e}")
            messagebox.showerror("Erro", f"Não foi possível salvar as configurações: {e}")

    # ================= LOGGING & UI HELPERS =================
    def log(self, message):
        """Append a message to the console logs in a thread-safe manner."""
        def append():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{message}\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, append)
        
    def change_appearance_mode(self, new_appearance_mode):
        ctk.set_appearance_mode(new_appearance_mode)
        self.log(f"Modo de aparência alterado para: {new_appearance_mode}")

    def toggle_sidebar(self):
        """Toggles the visibility of the left sidebar to save space."""
        if self.sidebar.grid_info():
            self.sidebar.grid_forget()
            self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
            self.log("Painel lateral recolhido.")
        else:
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.top_bar.grid_forget()
            self.log("Painel lateral expandido.")

    def toggle_key_visibility(self):
        if self.show_key_var.get():
            self.api_key_entry.configure(show="")
        else:
            self.api_key_entry.configure(show="*")

    def update_selection_count(self):
        """Updates the status counter label showing selected items."""
        total = len(self.row_widgets)
        selected = sum(1 for rw in self.row_widgets if rw.is_selected())
        self.counter_label.configure(text=f"Artigos selecionados: {selected} / {total}")
        if selected > 0:
            self.download_btn.configure(state="normal")
        else:
            self.download_btn.configure(state="disabled")
        
        # Refresh AI tab list dynamically!
        self.refresh_ai_papers_list()

    def select_all_action(self):
        for rw in self.row_widgets:
            rw.set_selected(True)
        self.update_selection_count()
        self.log("Todos os artigos foram marcados.")

    def deselect_all_action(self):
        for rw in self.row_widgets:
            rw.set_selected(False)
        self.update_selection_count()
        self.log("Todos os artigos foram desmarcados.")

    def on_tab_changed(self):
        if self.tabview.get() == "Análise por IA":
            self.refresh_ai_papers_list()

    # ================= SEARCH METHOD (ASYNC) =================
    def start_search(self):
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("Campo Vazio", "Por favor, insira uma palavra-chave para buscar.")
            return
            
        limit_str = self.limit_entry.get().strip()
        try:
            limit = int(limit_str)
            if limit <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("Limite Inválido", "O limite máximo deve ser um número inteiro maior que 0.")
            return

        # Prepare UI for searching state
        self.search_btn.configure(state="disabled", text="Buscando...")
        self.download_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Status: Buscando artigos nas APIs...", text_color="orange")
        self.log(f"Iniciando busca por '{keyword}' (limite de {limit} artigos)...")
        
        # Clear previous widgets
        for widget in self.row_widgets:
            widget.destroy()
        self.row_widgets.clear()
        self.placeholder_label.grid_forget()
        
        # Show loading placeholder
        self.loading_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="Buscando artigos no OpenAlex e Crossref... Por favor, aguarde.",
            font=ctk.CTkFont(size=13, slant="italic"),
            text_color="orange",
            pady=100
        )
        self.loading_label.grid(row=0, column=0, sticky="nsew")

        # Get language selection
        lang_sel = self.lang_optionemenu.get()
        language = None
        if lang_sel == "Inglês":
            language = "en"
        elif lang_sel == "Português":
            language = "pt"

        # Run search in background thread to prevent UI freezing
        email = self.email_entry.get().strip() or None
        t = threading.Thread(target=self._search_thread, args=(keyword, limit, email, language))
        t.daemon = True
        t.start()

    def _search_thread(self, keyword, limit, email, language):
        try:
            # Query APIs
            results = search_engine.search_all(keyword, limit, email, language)
            self.results = results
            
            # Update GUI on main thread
            self.after(0, lambda: self._on_search_completed(results))
        except Exception as e:
            self.log(f"Erro na busca em segundo plano: {e}")
            self.after(0, self._on_search_failed)

    def _on_search_completed(self, results):
        self.loading_label.destroy()
        self.search_btn.configure(state="normal", text="Pesquisar Artigos")
        
        if not results:
            self.placeholder_label.configure(text="Nenhum artigo de livre acesso com PDF disponível foi encontrado.")
            self.placeholder_label.grid(row=0, column=0, sticky="nsew")
            self.status_label.configure(text="Status: Busca finalizada. Nenhum resultado.", text_color="gray")
            self.log("Nenhum artigo encontrado.")
            self.update_selection_count()
            return
            
        # Clean all titles to ensure consistent presentation and filename creation
        for paper in results:
            if "title" in paper:
                paper["title"] = clean_title(paper["title"])
                
        self.log(f"Busca finalizada. Encontrados {len(results)} artigos com link direto para download.")
        self.status_label.configure(text=f"Status: Busca concluída. {len(results)} resultados prontos.", text_color=COLOR_SUCCESS)
        
        # Populate scrollable view with results
        for idx, paper in enumerate(results):
            row = PaperRowFrame(
                self.scrollable_frame, 
                paper, 
                on_toggle_callback=self.update_selection_count,
                fg_color=BG_CARD_ROW,
                border_width=1,
                border_color=BORDER_COLOR,
                corner_radius=8
            )
            row.grid(row=idx, column=0, padx=10, pady=5, sticky="ew")
            self.row_widgets.append(row)
            
        self.update_selection_count()

    def _on_search_failed(self):
        self.loading_label.destroy()
        self.search_btn.configure(state="normal", text="Pesquisar Artigos")
        self.placeholder_label.configure(text="Ocorreu um erro ao buscar os artigos.")
        self.placeholder_label.grid(row=0, column=0, sticky="nsew")
        self.status_label.configure(text="Status: Erro na busca.", text_color=COLOR_DANGER)
        self.update_selection_count()

    # ================= DOWNLOAD METHOD (ASYNC) =================
    def start_download(self):
        # Collect selected articles
        selected_articles = []
        for rw in self.row_widgets:
            if rw.is_selected():
                # Copy the paper dict so we don't pollute subsequent download attempts
                selected_articles.append(rw.paper.copy())
                
        if not selected_articles:
            messagebox.showwarning("Nenhum Selecionado", "Por favor, selecione pelo menos um artigo para baixar.")
            return

        # Pre-process conflict resolution
        final_articles = []
        global_action = None # Can be: 'replace_all', 'rename_all'
        
        for art in selected_articles:
            title = art.get("title", "artigo")
            year = art.get("year", "ano_desconhecido")
            safe_title = downloader.sanitize_filename(title)
            filename = f"{safe_title} ({year}).pdf"
            dest_path = os.path.join(self.downloads_dir, filename)
            
            # Check if file exists
            if os.path.exists(dest_path):
                if global_action == 'replace_all':
                    art["target_path"] = dest_path
                elif global_action == 'rename_all':
                    # Find a unique filename
                    counter = 1
                    base_name, ext = os.path.splitext(filename)
                    new_path = dest_path
                    while os.path.exists(new_path):
                        new_path = os.path.join(self.downloads_dir, f"{base_name}_{counter}{ext}")
                        counter += 1
                    art["target_path"] = new_path
                else:
                    # Show Conflict Dialog
                    dialog = ConflictDialog(self, filename)
                    self.wait_window(dialog)
                    choice = dialog.result
                    
                    if choice == 'cancel' or choice is None:
                        self.log("Download cancelado pelo usuário devido a conflito de arquivo.")
                        return # Abort the entire download process
                    elif choice == 'replace':
                        art["target_path"] = dest_path
                    elif choice == 'replace_all':
                        global_action = 'replace_all'
                        art["target_path"] = dest_path
                    elif choice == 'rename':
                        # Find a unique filename
                        counter = 1
                        base_name, ext = os.path.splitext(filename)
                        new_path = dest_path
                        while os.path.exists(new_path):
                            new_path = os.path.join(self.downloads_dir, f"{base_name}_{counter}{ext}")
                            counter += 1
                        art["target_path"] = new_path
                    elif choice == 'rename_all':
                        global_action = 'rename_all'
                        # Find a unique filename
                        counter = 1
                        base_name, ext = os.path.splitext(filename)
                        new_path = dest_path
                        while os.path.exists(new_path):
                            new_path = os.path.join(self.downloads_dir, f"{base_name}_{counter}{ext}")
                            counter += 1
                        art["target_path"] = new_path
            else:
                # File does not exist, safe to download to default path
                art["target_path"] = dest_path
                
            final_articles.append(art)

        # Disable buttons during download
        self.search_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Status: Iniciando downloads...", text_color="orange")
        self.log(f"Preparando download de {len(final_articles)} artigos para a pasta: {self.downloads_dir}")
        
        # Start download thread
        t = threading.Thread(target=self._download_thread, args=(final_articles,))
        t.daemon = True
        t.start()

    def _download_thread(self, articles):
        total = len(articles)
        
        def progress_cb(current, total_count, status_text):
            fraction = current / total_count if total_count > 0 else 0
            self.after(0, lambda: self._update_download_progress(fraction, status_text))
            self.log(status_text)
            
        success, message = downloader.download_selected_to_folder(
            articles,
            self.downloads_dir,
            progress_callback=progress_cb
        )
        
        # Notify completion
        self.after(0, lambda: self._on_download_completed(success, message))

    def _update_download_progress(self, fraction, status_text):
        self.progress_bar.set(fraction)
        self.status_label.configure(text=f"Status: {status_text}", text_color="orange")

    def _on_download_completed(self, success, message):
        self.search_btn.configure(state="normal")
        self.update_selection_count()
        
        if success:
            self.status_label.configure(text="Status: Download concluído com sucesso!", text_color=COLOR_SUCCESS)
            self.progress_bar.set(1.0)
            ans = messagebox.askyesno(
                "Sucesso",
                f"{message}\n\nDeseja abrir a pasta onde os arquivos foram salvos?"
            )
            if ans:
                try:
                    os.startfile(self.downloads_dir)
                except Exception as e:
                    self.log(f"Não foi possível abrir a pasta: {e}")
        else:
            self.status_label.configure(text="Status: Download falhou ou foi parcial.", text_color=COLOR_DANGER)
            messagebox.showerror("Erro no Download", message)
            
        self.log(f"Resultado final do download: {message}")

    # ================= AI ANALYSIS SYSTEM =================
    def refresh_ai_papers_list(self):
        """Refreshes the AI analysis paper list based on search tab selections."""
        if self.ai_running:
            return
            
        # Gather selected articles
        selected_articles = []
        for rw in self.row_widgets:
            if rw.is_selected():
                selected_articles.append(rw.paper)
                
        # Clear previous AI list widgets
        for w in self.ai_row_widgets:
            w.destroy()
        self.ai_row_widgets.clear()
        
        if not selected_articles:
            self.ai_placeholder.grid(row=0, column=0, sticky="nsew")
            self.ai_detail_title.configure(text="Selecione um artigo ao lado para ver a resposta da IA")
            self.ai_response_textbox.configure(state="normal")
            self.ai_response_textbox.delete("1.0", "end")
            self.ai_response_textbox.configure(state="disabled")
            self.copy_btn.configure(state="disabled")
            self.save_txt_btn.configure(state="disabled")
            return
            
        self.ai_placeholder.grid_forget()
        
        # Rebuild list
        for idx, paper in enumerate(selected_articles):
            # Ensure each selected article has its analysis response cleared/initialized
            if "ai_response" not in paper:
                paper["ai_response"] = None
                
            row = AIPaperRowFrame(
                self.ai_papers_scrollable,
                paper,
                click_callback=self.select_ai_paper,
                fg_color=BG_CARD_ROW,
                border_width=1,
                border_color=BORDER_COLOR,
                corner_radius=8
            )
            row.grid(row=idx, column=0, padx=5, pady=3, sticky="ew")
            
            # Restore visual status badge if response exists
            if paper.get("ai_response") is not None:
                resp = paper["ai_response"]
                if resp.startswith("Erro") or resp.startswith("Não foi possível") or "falhou" in resp.lower():
                    row.update_status("Erro", COLOR_DANGER)
                elif resp == "Análise cancelada pelo usuário.":
                    row.update_status("Cancelado", "gray")
                else:
                    row.update_status("Sucesso", COLOR_SUCCESS)
                    
            self.ai_row_widgets.append(row)

    def cancel_ai_analysis(self):
        """Requests to stop the current batch execution."""
        if self.ai_running:
            self.ai_analysis_cancelled = True
            self.stop_btn.configure(state="disabled", text="Cancelando...")
            self.log("Aviso: Solicitando interrupção do processamento por IA...")

    def start_ai_analysis(self):
        # 1. Gather selected articles
        selected_articles = []
        for rw in self.row_widgets:
            if rw.is_selected():
                selected_articles.append(rw.paper)
                
        if not selected_articles:
            messagebox.showwarning("Nenhum Selecionado", "Por favor, selecione ao menos um artigo na aba 'Busca & Downloads' para realizar a análise.")
            return
            
        # 2. Get API Configurations
        base_url = self.api_url_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        model = self.api_model_entry.get().strip()
        
        if not base_url or not model:
            messagebox.showwarning("Campos Vazios", "Por favor, preencha a URL Base da API e o Nome do Modelo.")
            return
            
        api_config = {
            "base_url": base_url,
            "api_key": api_key,
            "model": model
        }
        
        # 3. Read and sanitize user prompt (auto-enforcement of the safety instruction)
        raw_prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
        if not raw_prompt:
            messagebox.showwarning("Prompt Vazio", "Por favor, digite o prompt de análise por IA.")
            return
            
        sanitized_prompt = ai_analyzer.sanitize_prompt(raw_prompt)
        
        # If prompt was changed by enforcement, update prompt textbox to show the appended phrase
        if sanitized_prompt != raw_prompt:
            self.prompt_textbox.delete("1.0", "end")
            self.prompt_textbox.insert("1.0", sanitized_prompt)
            self.log("Aviso: Instrução de segurança adicionada ao prompt.")
            
        # 4. Prepare UI for AI Analysis
        self.log(f"Iniciando análise por IA de {len(selected_articles)} artigos...")
        self.status_label.configure(text="Status: Inicializando análise por IA...", text_color="orange")
        self.progress_bar.set(0)
        
        # Update run states
        self.ai_running = True
        self.ai_analysis_cancelled = False
        
        self.search_btn.configure(state="disabled")
        self.analyze_btn.configure(state="disabled", text="Analisando...")
        self.stop_btn.configure(state="normal", text="🛑 Parar Análise")
        
        # Reset detail viewer
        self.selected_ai_paper = None
        self.ai_detail_title.configure(text="Selecione um artigo ao lado para ver a análise")
        self.ai_response_textbox.configure(state="normal")
        self.ai_response_textbox.delete("1.0", "end")
        self.ai_response_textbox.configure(state="disabled")
        self.copy_btn.configure(state="disabled")
        self.save_txt_btn.configure(state="disabled")
        
        # Refresh the left pane list to clear old runs and reset statuses to "Pendente"
        for row in self.ai_row_widgets:
            row.paper["ai_response"] = None
            row.update_status("Pendente", TEXT_MUTED)
            
        # Start AI thread
        t = threading.Thread(
            target=self._ai_analysis_thread, 
            args=(selected_articles, api_config, sanitized_prompt)
        )
        t.daemon = True
        t.start()

    def _ai_analysis_thread(self, articles, api_config, prompt):
        total = len(articles)
        success_count = 0
        
        for idx, paper in enumerate(articles):
            row_widget = self.ai_row_widgets[idx]
            title = paper.get("title", "Untitled")
            year = paper.get("year", "ano_desconhecido")
            
            # Check cancellation at iteration start
            if self.ai_analysis_cancelled:
                self.after(0, lambda r=row_widget: r.update_status("Cancelado", "gray"))
                paper["ai_response"] = "Análise cancelada pelo usuário."
                self.log(f"[{idx+1}/{total}] Cancelado: {title[:40]}")
                continue
            
            # Check if text is already cached!
            doc_text = paper.get("extracted_text")
            
            if doc_text:
                self.log(f"[{idx+1}/{total}] Usando texto cacheado para: {title[:40]}")
                # Skip download and extraction, update progress bar
                progress_fraction = (idx + 0.6) / total
                self.after(0, lambda f=progress_fraction: self.progress_bar.set(f))
            else:
                # Format final PDF destination path in the local downloads directory
                safe_title = downloader.sanitize_filename(title)
                pdf_filename = f"{safe_title} ({year}).pdf"
                pdf_path = os.path.join(self.downloads_dir, pdf_filename)
                
                download_success = False
                download_errors = []
                
                # Check if PDF already exists locally!
                if os.path.exists(pdf_path):
                    self.log(f"[{idx+1}/{total}] PDF já existe localmente: {pdf_filename}")
                    download_success = True
                else:
                    # Step 1: Download PDF
                    self.after(0, lambda r=row_widget: r.update_status("Baixando...", "orange"))
                    self.after(0, lambda t=title: self.status_label.configure(text=f"Status: Baixando PDF ({idx+1}/{total}): {t[:30]}...", text_color="orange"))
                    self.log(f"[{idx+1}/{total}] Baixando PDF: {title[:40]}...")
                    
                    pdf_urls = paper.get("pdf_urls") or []
                    if not pdf_urls and paper.get("pdf_url"):
                        pdf_urls = [paper.get("pdf_url")]
                        
                    # Check cancellation right before downloading
                    if self.ai_analysis_cancelled:
                        self.after(0, lambda r=row_widget: r.update_status("Cancelado", "gray"))
                        paper["ai_response"] = "Análise cancelada pelo usuário."
                        continue
                        
                    from urllib.parse import urlparse
                    for url in pdf_urls:
                        domain = urlparse(url).netloc or "unknown"
                        success, err = downloader.download_pdf(url, pdf_path)
                        if success:
                            download_success = True
                            break
                        else:
                            download_errors.append(f"{domain}: {err}")
                            
                # Update progress bar
                progress_fraction = (idx + 0.3) / total
                self.after(0, lambda f=progress_fraction: self.progress_bar.set(f))
                
                if not download_success:
                    err_msg = "; ".join(download_errors) if download_errors else "Nenhum link PDF disponível"
                    self.log(f"[{idx+1}/{total}] Falha no download de {title[:40]}. Detalhes: {err_msg}")
                    paper["ai_response"] = f"Não foi possível analisar este artigo porque o download do PDF falhou.\n\nDetalhes do Erro:\n{err_msg}"
                    self.after(0, lambda r=row_widget: r.update_status("Erro", COLOR_DANGER))
                    continue
                    
                # Check cancellation right before extracting text
                if self.ai_analysis_cancelled:
                    self.after(0, lambda r=row_widget: r.update_status("Cancelado", "gray"))
                    paper["ai_response"] = "Análise cancelada pelo usuário."
                    continue
                    
                # Step 2: Extract Text
                self.after(0, lambda r=row_widget: r.update_status("Extraindo...", "blue"))
                self.after(0, lambda t=title: self.status_label.configure(text=f"Status: Extraindo texto ({idx+1}/{total}): {t[:30]}...", text_color="orange"))
                self.log(f"[{idx+1}/{total}] Extraindo texto do PDF...")
                
                extracted_res = ai_analyzer.extract_text_from_pdf(pdf_path)
                
                # Update progress bar
                progress_fraction = (idx + 0.6) / total
                self.after(0, lambda f=progress_fraction: self.progress_bar.set(f))
                
                if extracted_res.startswith("Erro") or extracted_res.startswith("Erro"):
                    self.log(f"[{idx+1}/{total}] Falha ao extrair texto do PDF: {extracted_res}")
                    paper["ai_response"] = f"Não foi possível analisar o artigo. Erro na extração de texto:\n{extracted_res}"
                    self.after(0, lambda r=row_widget: r.update_status("Erro Texto", COLOR_DANGER))
                    continue
                    
                # Successfully extracted! Cache it!
                doc_text = extracted_res
                paper["extracted_text"] = doc_text
                
                # Check cancellation right before API request
                if self.ai_analysis_cancelled:
                    self.after(0, lambda r=row_widget: r.update_status("Cancelado", "gray"))
                    paper["ai_response"] = "Análise cancelada pelo usuário."
                    continue
                    
                # Step 3: Query LLM
                self.after(0, lambda r=row_widget: r.update_status("Lendo LLM...", "purple"))
                self.after(0, lambda t=title: self.status_label.configure(text=f"Status: Analisando com LLM ({idx+1}/{total}): {t[:30]}...", text_color="purple"))
                self.log(f"[{idx+1}/{total}] Enviando conteúdo do artigo para {api_config['model']}...")
                
                api_success, response_content = ai_analyzer.analyze_document(
                    api_config=api_config,
                    prompt=prompt,
                    document_text=doc_text,
                    metadata=paper
                )
                
                # Check cancellation right after API request
                if self.ai_analysis_cancelled:
                    self.after(0, lambda r=row_widget: r.update_status("Cancelado", "gray"))
                    paper["ai_response"] = "Análise cancelada pelo usuário."
                    continue
                    
                # Step 4: Record Results
                paper["ai_response"] = response_content
                
                if api_success:
                    self.after(0, lambda r=row_widget: r.update_status("Sucesso", COLOR_SUCCESS))
                    self.log(f"[{idx+1}/{total}] Sucesso! Artigo analisado com sucesso.")
                    success_count += 1
                else:
                    self.after(0, lambda r=row_widget: r.update_status("Erro API", COLOR_DANGER))
                    self.log(f"[{idx+1}/{total}] Falha na API da LLM: {response_content}")
                    
                # Update progress bar to completed state for this paper
                progress_fraction = (idx + 1.0) / total
                self.after(0, lambda f=progress_fraction: self.progress_bar.set(f))
                
                # If the paper currently highlighted by the user in the detail panel is this one, reload text area
                self.after(0, lambda p=paper: self._reload_detail_view_if_active(p))
                
        # Finalization
        if self.ai_analysis_cancelled:
            summary_msg = f"Análise interrompida pelo usuário! Concluídos com sucesso: {success_count}/{total}."
            self.after(0, lambda: self.status_label.configure(text=f"Status: {summary_msg}", text_color=COLOR_DANGER))
        else:
            summary_msg = f"Análise concluída! Analisados: {success_count}/{total} com sucesso."
            self.after(0, lambda: self.status_label.configure(text=f"Status: {summary_msg}", text_color=COLOR_SUCCESS))
            
        self.log(summary_msg)
        self.after(0, self._on_ai_analysis_completed)

    def _reload_detail_view_if_active(self, paper):
        if self.selected_ai_paper and self.selected_ai_paper.get("doi") == paper.get("doi"):
            self.select_ai_paper(paper)

    def _on_ai_analysis_completed(self):
        self.ai_running = False
        self.search_btn.configure(state="normal")
        self.analyze_btn.configure(state="normal", text="🧠 Analisar Artigos Selecionados com IA")
        self.stop_btn.configure(state="disabled", text="🛑 Parar Análise")

    def select_ai_paper(self, paper):
        """Displays the AI response for the selected paper in the right side detail panel."""
        self.selected_ai_paper = paper
        
        # Show paper title (truncated to a single line to keep layout/textbox size stable)
        title_text = paper.get("title", "Untitled Document")
        year = paper.get("year", "N/A")
        full_title = f"{title_text} ({year})"
        if len(full_title) > 85:
            display_title = full_title[:82] + "..."
        else:
            display_title = full_title
            
        self.ai_detail_title.configure(text=display_title)
        
        # Load response
        response = paper.get("ai_response")
        self.ai_response_textbox.configure(state="normal")
        self.ai_response_textbox.delete("1.0", "end")
        
        if response is None:
            self.ai_response_textbox.insert("1.0", "A análise para este artigo está na fila ou em execução. Aguarde...")
            self.copy_btn.configure(state="disabled")
            self.save_txt_btn.configure(state="disabled")
        else:
            self.ai_response_textbox.insert("1.0", response)
            self.copy_btn.configure(state="normal")
            self.save_txt_btn.configure(state="normal")
            
        self.ai_response_textbox.configure(state="disabled")

    def copy_ai_response(self):
        content = self.ai_response_textbox.get("1.0", "end-1c").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Sucesso", "Análise copiada para a área de transferência!")

    def save_ai_response(self):
        content = self.ai_response_textbox.get("1.0", "end-1c").strip()
        if not content or not self.selected_ai_paper:
            return
            
        paper_title = self.selected_ai_paper.get("title", "analise")
        safe_title = downloader.sanitize_filename(paper_title)
        
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar Análise por IA",
            defaultextension=".txt",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Arquivos Markdown", "*.md")],
            initialfile=f"Analise_{safe_title}.txt"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Sucesso", "Análise salva por IA com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar o arquivo: {e}")
