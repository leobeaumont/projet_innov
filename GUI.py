import tkinter as tk
from tkinter import font as tkfont
import threading

# ── Colours & style constants ──────────────────────────────────────────────
BG          = "#F5F7FA"   # very light neutral background
SIDEBAR_BG  = "#2F3E46"   # dark slate for header/footer
BUBBLE_BOT  = "#FFFFFF"   # assistant bubble (white)
BUBBLE_USR  = "#E6F0FF"   # user bubble (subtle blue)
TEXT_BOT    = "#0F1720"   # primary text (dark)
TEXT_USR    = "#0B2A97"   # user text (blue)
ACCENT      = "#1F77B4"   # professional blue accent
INPUT_BG    = "#FFFFFF"   # input background
INPUT_FG    = "#0F1720"   # input foreground
SEND_BG     = "#1F77B4"   # send button background
SEND_FG     = "#FFFFFF"   # send button text
CARD_BG     = "#FFFFFF"   # cards / panels background
CARD_BORDER = "#DCE2EA"   # subtle card border
GREEN       = "#2CA02C"
YELLOW      = "#FFB703"
PEACH       = "#FF7F0E"
MAUVE       = "#6A51A3"

FONT_FAMILY = "Helvetica"


class CoachApp(tk.Tk):
    # ── step sequence ──────────────────────────────────────────────────────
    STEPS = [
        "profile",    # ask for user profile
        "food",       # ask for food intake
        "activity",   # ask for physical activity
        "done",       # show summary + coach advice
    ]

    def __init__(self):
        super().__init__()
        self.title("🥗 Coach Nutrition & Sport")
        self.geometry("900x680")
        self.minsize(700, 500)
        self.configure(bg=BG)

        self._step_index = 0
        self._response1 = None
        self._response2 = None
        self._response3 = None
        self._waiting   = False   # True while the LLM is running

        self._build_ui()
        self._greet()

    # ── UI construction ────────────────────────────────────────────────────
    def _build_ui(self):
        # title bar
        header = tk.Frame(self, bg=SIDEBAR_BG, height=54)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header, text="🥗  Coach Nutrition & Sport",
            bg=SIDEBAR_BG, fg=ACCENT,
            font=(FONT_FAMILY, 16, "bold"), pady=10
        ).pack(side="left", padx=20)

        tk.Label(
            header, text="Powered by Gemini 2.5",
            bg=SIDEBAR_BG, fg="#585b70",
            font=(FONT_FAMILY, 10)
        ).pack(side="right", padx=20)

        # chat area
        chat_frame = tk.Frame(self, bg=BG)
        chat_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self._canvas = tk.Canvas(chat_frame, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(chat_frame, orient="vertical",
                                 command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._msg_frame = tk.Frame(self._canvas, bg=BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._msg_frame, anchor="nw"
        )

        self._msg_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # mouse wheel scrolling
        self._canvas.bind_all("<MouseWheel>",  self._on_mousewheel)
        self._canvas.bind_all("<Button-4>",    lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind_all("<Button-5>",    lambda e: self._canvas.yview_scroll(1,  "units"))

        # input bar
        input_bar = tk.Frame(self, bg=SIDEBAR_BG, pady=12)
        input_bar.pack(fill="x", side="bottom")

        self._input_var = tk.StringVar()
        self._input_box = tk.Text(
            input_bar, height=3,
            bg=INPUT_BG, fg=INPUT_FG,
            insertbackground=INPUT_FG,
            font=(FONT_FAMILY, 12),
            relief="flat", padx=12, pady=8,
            wrap="word"
        )
        self._input_box.pack(side="left", fill="x", expand=True,
                             padx=(16, 8), pady=0)
        self._input_box.bind("<Return>",       self._on_enter)
        self._input_box.bind("<Shift-Return>", lambda e: None)  # allow newline

        self._send_btn = tk.Button(
            input_bar, text="Envoyer ➤",
            bg=SEND_BG, fg=SEND_FG,
            font=(FONT_FAMILY, 12, "bold"),
            relief="flat", padx=16, pady=8,
            cursor="hand2",
            command=self._send
        )
        self._send_btn.pack(side="right", padx=(0, 16))

        # status label
        self._status_var = tk.StringVar(value="")
        tk.Label(
            input_bar, textvariable=self._status_var,
            bg=SIDEBAR_BG, fg=YELLOW,
            font=(FONT_FAMILY, 10, "italic")
        ).pack(side="right", padx=8)

    # ── scroll helpers ─────────────────────────────────────────────────────
    def _on_frame_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_bottom(self):
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    # ── message bubbles ────────────────────────────────────────────────────
    def _add_bubble(self, text: str, role: str = "bot"):
        """Add a chat bubble. role = 'bot' | 'user'"""
        is_user = role == "user"
        outer = tk.Frame(self._msg_frame, bg=BG)
        outer.pack(fill="x", padx=16, pady=4)

        bubble_color = BUBBLE_USR if is_user else BUBBLE_BOT
        text_color   = TEXT_USR   if is_user else TEXT_BOT
        anchor       = "e"        if is_user else "w"

        inner = tk.Frame(outer, bg=bubble_color)
        inner.pack(anchor=anchor, padx=8)

        lbl = tk.Label(
            inner, text=text,
            bg=bubble_color, fg=text_color,
            font=(FONT_FAMILY, 12),
            wraplength=560, justify="left",
            padx=14, pady=10
        )
        lbl.pack()

        self._scroll_bottom()

    def _add_typing_indicator(self):
        """Show a '…' bubble while waiting for the LLM."""
        outer = tk.Frame(self._msg_frame, bg=BG)
        outer.pack(fill="x", padx=16, pady=4, anchor="w")
        inner = tk.Frame(outer, bg=BUBBLE_BOT)
        inner.pack(anchor="w", padx=8)
        self._typing_label = tk.Label(
            inner, text="⏳  Le coach réfléchit…",
            bg=BUBBLE_BOT, fg="#585b70",
            font=(FONT_FAMILY, 11, "italic"),
            padx=14, pady=10
        )
        self._typing_label.pack()
        self._typing_frame = outer
        self._scroll_bottom()

    def _remove_typing_indicator(self):
        if hasattr(self, "_typing_frame"):
            self._typing_frame.destroy()

    # ── summary card ──────────────────────────────────────────────────────
    def _add_summary_card(self, r1, r2, r3):
        outer = tk.Frame(self._msg_frame, bg=BG)
        outer.pack(fill="x", padx=24, pady=10)

        card = tk.Frame(outer, bg=CARD_BG, bd=1, relief="solid",
                        highlightbackground=CARD_BORDER, highlightthickness=1)
        card.pack(fill="x")

        def row(label, value, color=TEXT_BOT):
            f = tk.Frame(card, bg=CARD_BG)
            f.pack(fill="x", padx=16, pady=2)
            tk.Label(f, text=label, bg=CARD_BG, fg="#585b70",
                     font=(FONT_FAMILY, 11), width=26, anchor="w").pack(side="left")
            tk.Label(f, text=value, bg=CARD_BG, fg=color,
                     font=(FONT_FAMILY, 11, "bold"), anchor="w").pack(side="left")

        def section(title, color=ACCENT):
            tk.Frame(card, bg=CARD_BG, height=8).pack()  # top spacing
            tk.Label(card, text=title, bg=CARD_BG, fg=color,
                     font=(FONT_FAMILY, 12, "bold"),
                     padx=16, pady=2, anchor="w").pack(fill="x")
            tk.Frame(card, bg=CARD_BORDER, height=1).pack(fill="x", padx=16)

        name = r1.uname or "Utilisateur"
        tk.Label(card,
                 text=f"  📋  RÉSUMÉ QUOTIDIEN — {name.upper()}",
                 bg=CARD_BG, fg=ACCENT,
                 font=(FONT_FAMILY, 13, "bold"), pady=10).pack(anchor="w")

        section("👤  PROFIL", MAUVE)
        row("Objectif :",      r1.ugoal      or "Non précisé", GREEN)
        row("Physique :",      f"{r1.uheight or '??'} cm  ·  {r1.uweight or '??'} kg")
        row("Allergies :",     ", ".join(r1.uallergies)  or "Aucune", PEACH)
        row("Conditions :",    ", ".join(r1.uconditions) or "Aucune", PEACH)
        row("Traitements :",   ", ".join(r1.umedications)or "Aucun",  PEACH)

        section("🥗  CONSOMMATION ESTIMÉE", GREEN)
        row("Énergie :",       f"{r2.kcal     or 0} kcal", YELLOW)
        row("Protéines :",     f"{r2.prot     or 0} g")
        row("Glucides :",      f"{r2.glucides or 0} g")
        row("Lipides :",       f"{r2.lipides  or 0} g")
        row("Eau :",           f"{r2.eau      or 0} L")

        section("🏃  ACTIVITÉ PHYSIQUE", PEACH)
        row("Calories dépensées :", f"{r3.kcal or 0} kcal", YELLOW)

        if r2.kcal is not None and r3.kcal is not None:
            bilan = r2.kcal - r3.kcal
            color = GREEN if bilan < 0 else (YELLOW if bilan < 300 else PEACH)
            section("⚡  BILAN ÉNERGÉTIQUE", ACCENT)
            row("Net :", f"{bilan:+d} kcal", color)

        tk.Frame(card, bg=CARD_BG, height=10).pack()
        self._scroll_bottom()

    # ── coach advice ──────────────────────────────────────────────────────
    def _add_coach_bubble(self, text: str):
        outer = tk.Frame(self._msg_frame, bg=BG)
        outer.pack(fill="x", padx=16, pady=8)

        card = tk.Frame(outer, bg=BUBBLE_BOT, bd=1, relief="solid",
                        highlightbackground=ACCENT, highlightthickness=1)
        card.pack(anchor="w", padx=8)

        tk.Frame(card, bg=BUBBLE_BOT, height=10).pack()
        tk.Label(card, text="🏋️  Conseil de votre Coach",
                 bg=BUBBLE_BOT, fg=ACCENT,
                 font=(FONT_FAMILY, 12, "bold"),
                 padx=14, pady=2).pack(anchor="w")

        tk.Frame(card, bg=CARD_BORDER, height=1).pack(fill="x", padx=14)

        txt = tk.Text(
            card,
            bg=BUBBLE_BOT, fg=TEXT_BOT,
            font=(FONT_FAMILY, 12),
            relief="flat", wrap="word",
            padx=14, pady=10,
            width=60, height=1,          # height will be adjusted below
            state="normal",
            cursor="arrow",
        )
        txt.tag_configure("bold", font=(FONT_FAMILY, 12, "bold"))

        # Parse **...** and insert with/without bold tag
        import re
        parts = re.split(r'\*\*(.*?)\*\*', text)
        for i, part in enumerate(parts):
            if i % 2 == 1:              # odd indices are the bold segments
                txt.insert("end", part, "bold")
            else:
                txt.insert("end", part)

        # Fit height to content
        txt.update_idletasks()
        line_count = int(txt.index("end-1c").split(".")[0])
        txt.config(height=line_count, state="disabled")
        txt.pack(anchor="w", fill="x", padx=0, pady=0)

        self._scroll_bottom()

    # ── conversation flow ──────────────────────────────────────────────────
    def _greet(self):
        intro = (
            "Bonjour ! Je suis votre assistant personnel en nutrition et sport.\n\n"
            "Commençons par votre profil. Décrivez-vous librement :\n"
            "  • Nom d'utilisateur\n"
            "  • Âge, taille, poids\n"
            "  • Objectif (perdre du poids, prendre du muscle…)\n"
            "  • Allergies, maladies, médicaments éventuels"
        )
        self._add_bubble(intro, "bot")

    def _on_enter(self, event):
        # Shift+Enter inserts a newline; plain Enter sends
        if not event.state & 0x0001:   # Shift not held
            self._send()
            return "break"

    def _send(self):
        if self._waiting:
            return
        text = self._input_box.get("1.0", "end").strip()
        if not text:
            return
        self._input_box.delete("1.0", "end")
        self._add_bubble(text, "user")
        step = self.STEPS[self._step_index]
        if step == "profile":
            self._run_in_thread(self._process_profile, text)
        elif step == "food":
            self._run_in_thread(self._process_food, text)
        elif step == "activity":
            self._run_in_thread(self._process_activity, text)

    def _run_in_thread(self, fn, *args):
        self._waiting = True
        self._send_btn.config(state="disabled")
        self._status_var.set("En cours…")
        self._add_typing_indicator()
        t = threading.Thread(target=fn, args=args, daemon=True)
        t.start()

    def _llm_done(self):
        self._remove_typing_indicator()
        self._waiting = False
        self._send_btn.config(state="normal")
        self._status_var.set("")

    # ── LLM calls (run in worker thread, schedule UI updates on main thread) ──
    def _process_profile(self, user_text: str):
        try:
            from main import chain1
            r1 = chain1.invoke({"domaine": "nutrition et sports", "question": user_text})
            self._response1 = r1
            self.after(0, self._after_profile, r1)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _after_profile(self, r1):
        self._llm_done()
        name = r1.uname or "vous"
        self._add_bubble(
            f"Très bien {name} ! 😊\n\n"
            "Maintenant décrivez-moi avec précision tout ce que vous avez "
            "mangé et bu aujourd'hui (repas, snacks, boissons…).",
            "bot"
        )
        self._step_index = 1

    def _process_food(self, user_text: str):
        try:
            from main import chain2
            r2 = chain2.invoke({"domaine": "nutrition et sports", "question": user_text})
            self._response2 = r2
            self.after(0, self._after_food, r2)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _after_food(self, r2):
        self._llm_done()
        name = (self._response1.uname or "vous") if self._response1 else "vous"
        self._add_bubble(
            f"D'accord {name} ! J'ai enregistré votre consommation. 🥗\n\n"
            "Pour finir, décrivez-moi toute activité physique que vous avez "
            "pratiquée aujourd'hui (sport, marche, vélo…).",
            "bot"
        )
        self._step_index = 2

    def _process_activity(self, user_text: str):
        try:
            from main import chain3, chain_coach
            r3 = chain3.invoke({"domaine": "nutrition et sports", "question": user_text})
            self._response3 = r3
            advice = chain_coach.invoke({
                "profil":   self._response1.model_dump_json(),
                "conso":    self._response2.model_dump_json(),
                "activite": r3.model_dump_json(),
            })
            self.after(0, self._after_activity, r3, advice.content)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _after_activity(self, r3, coach_text: str):
        self._llm_done()
        self._add_bubble("Analyse en cours… voici votre résumé du jour ! 📊", "bot")
        self._add_summary_card(self._response1, self._response2, r3)
        self._add_coach_bubble(coach_text)
        self._step_index = 3
        # Disable input after the full flow
        self._input_box.config(state="disabled")
        self._send_btn.config(state="disabled", text="Terminé ✓")
        self._status_var.set("Session terminée — relancez l'application pour recommencer.")

    def _show_error(self, msg: str):
        self._llm_done()
        self._add_bubble(f"⚠️ Une erreur est survenue :\n{msg}", "bot")


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = CoachApp()
    app.mainloop()

