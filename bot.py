#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI Runner (prompt_toolkit) untuk Pharos — terhubung ke main.py (P1..P6)

Fitur:
- Navigasi menu: ↑/↓/PageUp/PageDown/Home/End, Enter untuk pilih
- LOG tidak fokus (PageUp/PageDown TIDAK menggulir log)
- Warna LOG: hijau (sukses), merah (gagal) via deteksi pola
- Set Default Run -> submenu P1..P6 (ubah default via prompt blocking aman)
- Individual Run menjalankan program tunggal (di thread)
- All-in-One menjalankan P1..P6 berurutan lalu tidur 24 jam (loop) di background
"""

from __future__ import annotations
import os
import threading
import time
from typing import List, Tuple, Optional, Callable

# ----- App UI (prompt_toolkit) -----
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import to_formatted_text

# run_in_terminal: versi prompt_toolkit beda-beda; sediakan fallback
try:
    from prompt_toolkit.application import run_in_terminal  # PTK >=3.0
except Exception:
    try:
        from prompt_toolkit.shortcuts import run_in_terminal  # PTK 2.x
    except Exception:
        from prompt_toolkit.shortcuts.utils import run_in_terminal  # fallback terakhir

# ----- Ambil runner & config dari main.py -----
import main as RUN  # pastikan main.py ada di folder yang sama


# =========================
# LOG VIEW (tidak fokus)
# =========================
class LogView:
    """
    Log scrollable (via mouse) tetapi TIDAK fokus, jadi PgUp/PgDown tetap ke menu.
    Pewarnaan otomatis berdasarkan pola teks.
    """
    def __init__(self) -> None:
        self._lines: List[Tuple[str, str]] = []  # (style, text)
        self._control = FormattedTextControl(self._render)
        self.window = Frame(
            body=Window(
                content=self._control,
                wrap_lines=True,
                always_hide_cursor=True,
            ),
            title="LOG",
            style="class:frame",
        )

    def clear(self) -> None:
        self._lines.clear()
        self._control.text = ""

    def _render(self) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for style, text in self._lines[-2000:]:
            out.append((style, text + "\n"))
        return out

    def _classify(self, s: str) -> str:
        st = "class:log"
        low = s.lower()
        if "[ok]" in s or "✅" in s or "sukses" in low or "success" in low or "mined" in low:
            st = "class:ok"
        if "[err]" in s or "❌" in s or "gagal" in low or "revert" in low or "failed" in low or "error" in low:
            st = "class:err"
        return st

    def write(self, s: str) -> None:
        style = self._classify(s)
        self._lines.append((style, s))
        self._control.text = to_formatted_text(self._render())

    def info(self, s: str) -> None:
        self._lines.append(("class:log", s))
        self._control.text = to_formatted_text(self._render())

    def ok(self, s: str) -> None:
        self._lines.append(("class:ok", s))
        self._control.text = to_formatted_text(self._render())

    def err(self, s: str) -> None:
        self._lines.append(("class:err", s))
        self._control.text = to_formatted_text(self._render())


# =========================
# STATS VIEW (ringkas)
# =========================
class StatsView:
    def __init__(self) -> None:
        self.area = TextArea(
            text="",
            read_only=True,
            focusable=False,
            scrollbar=False,
            style="class:stats",
        )
        self.frame = Frame(self.area, title="STATS", style="class:frame")

    def update(self) -> None:
        lines: List[str] = []
        lines.append("Defaults")
        lines.append(f"- AIO sleep: 24 jam")
        lines.append("")
        lines.append("Per Program:")
        try:
            lines.append(f"1. P1 Lend & Borrow  → repeat={RUN.P1_DEFAULT.repeat}, delay={RUN.P1_DEFAULT.delay_secs}s")
        except Exception:
            lines.append("1. P1 Lend & Borrow  → (tidak aktif)")
        lines.append(f"2. P2 Add Domain     → count={RUN.P2_DEFAULT.count}, delay={RUN.P2_DEFAULT.delay_secs}s")
        lines.append(f"3. P3 Swap & Earn R2 → swaps={RUN.P3_DEFAULT.swap_times}, delay={RUN.P3_DEFAULT.delay_secs}s")
        lines.append(f"4. P4 Brokex Trade   → runs={RUN.P4_DEFAULT.runs}, delay={RUN.P4_DEFAULT.delay_secs}s")
        lines.append(f"5. P5 RwaTrade       → runs={RUN.P5_DEFAULT.runs}, delay={RUN.P5_DEFAULT.delay_secs}s")
        lines.append(f"6. P6 Spout          → runs={RUN.P6_DEFAULT.runs}, delay={RUN.P6_DEFAULT.delay_secs}s, amt={RUN.P6_DEFAULT.amount}")
        self.area.text = "\n".join(lines)


# =========================
# MENU VIEW
# =========================
class MenuView:
    def __init__(self, title: str, items: List[Tuple[str, Callable[[], None]]]) -> None:
        self.title = title
        self.items = items
        self.index = 0
        self.control = FormattedTextControl(self._render)
        self.window = Frame(
            body=Window(self.control, always_hide_cursor=True, wrap_lines=False),
            title=title,
            style="class:frame",
            width=46,  # menu lebih besar agar teks jelas
        )

    def _render(self) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for i, (label, _) in enumerate(self.items):
            if i == self.index:
                out.append(("class:sel", f"> {label}\n"))
            else:
                out.append(("class:menu", f"  {label}\n"))
        return out

    def set(self, title: str, items: List[Tuple[str, Callable[[], None]]]) -> None:
        self.title = title
        self.items = items
        self.index = 0
        self.window.title = title
        self.control.text = to_formatted_text(self._render())

    def move(self, delta: int) -> None:
        if not self.items:
            return
        self.index = (self.index + delta) % len(self.items)
        self.control.text = to_formatted_text(self._render())

    def move_page(self, delta: int) -> None:
        self.move(delta * 5)

    def move_home(self) -> None:
        if not self.items:
            return
        self.index = 0
        self.control.text = to_formatted_text(self._render())

    def move_end(self) -> None:
        if not self.items:
            return
        self.index = len(self.items) - 1
        self.control.text = to_formatted_text(self._render())

    def activate(self) -> None:
        if not self.items:
            return
        _, fn = self.items[self.index]
        fn()


# =========================
# JEMBATAN LOG UNTUK main.py
# =========================
class UIConsoleProxy:
    """Gantikan RUN.console agar console.print(...) diarahkan ke LogView."""
    def __init__(self, log: LogView) -> None:
        self.log = log
    def print(self, *objects, **kwargs) -> None:
        if not objects:
            self.log.write("")
            return
        msg = " ".join(str(o) for o in objects)
        msg = msg.replace("─", "-").replace("═", "=")
        self.log.write(msg)


# =========================
# APLIKASI
# =========================
class RunnerApp:
    def __init__(self) -> None:
        # Views
        self.log = LogView()
        self.stats = StatsView()

        # Main menu + submenus
        self.menu = MenuView("Main Menu", [])
        self.menu_root = [
            ("1) All in One Run (loop 24 jam)", self.run_aio),
            ("2) Set Default Run",             self.menu_set_defaults),
            ("3) Individual Run",              self.menu_individual),
            ("4) Keluar",                      self.exit_app),
        ]
        self.menu.set("Main Menu", self.menu_root)

        # Layout
        body = VSplit(
            [
                self.menu.window,
                HSplit([self.stats.frame, self.log.window], padding=1),
            ],
            padding=2,
        )
        self.layout = Layout(body)

        # Key bindings (semua diarahkan ke MENU)
        kb = KeyBindings()

        @kb.add("up")
        def _(event): self.menu.move(-1)

        @kb.add("down")
        def _(event): self.menu.move(+1)

        @kb.add("pageup")
        def _(event): self.menu.move_page(-1)

        @kb.add("pagedown")
        def _(event): self.menu.move_page(+1)

        @kb.add("home")
        def _(event): self.menu.move_home()

        @kb.add("end")
        def _(event): self.menu.move_end()

        @kb.add("enter")
        def _(event): self.menu.activate()

        @kb.add("q")
        def _(event): self.exit_app()

        self.kb = kb

        # App
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,   # scroll log dengan mouse OK
            style=Style.from_dict({
                "frame": "bg:#10121a #cfd8dc",
                "menu": "#cfd8dc",
                "sel": "reverse bold",
                "log": "#cfd8dc",
                "ok": "bold #00e676",
                "err": "bold #ff5252",
                "stats": "#cfd8dc",
            }),
        )

        # Pasang proxy console untuk main.py
        RUN.console = UIConsoleProxy(self.log)
        self.stats.update()

        # Flag untuk stop AIO loop
        self._stop_flag = False

    # ---------- Prompt blocking aman (tanpa async) ----------
    def _prompt_blocking(self, label: str, default: Optional[str] = None) -> Optional[str]:
        """
        Jalankan input() di luar event loop prompt_toolkit (aman).
        """
        box = {"v": None}

        def _ask():
            try:
                s = input(f"{label}{f' [{default}]' if default is not None else ''}: ").strip()
                box["v"] = s if s else (str(default) if default is not None else "")
            except KeyboardInterrupt:
                box["v"] = None

        # gunakan fungsi global run_in_terminal (bukan method Application)
        run_in_terminal(_ask)
        return box["v"]

    def _prompt_int(self, label: str, current: int, minv: int, maxv: int) -> int:
        while True:
            s = self._prompt_blocking(label, str(current))
            if s is None:
                return current
            if s.isdigit():
                v = int(s)
                if minv <= v <= maxv:
                    return v
            self.log.err(f"[err]Input tidak valid. Harus angka {minv}..{maxv}.[/err]")

    def _prompt_seconds(self, label: str, current: int, minv: int, maxv: int) -> int:
        return self._prompt_int(label, current, minv, maxv)

    def _prompt_decimal(self, label: str, current) -> Optional[object]:
        s = self._prompt_blocking(label, str(current))
        if s is None:
            return current
        try:
            from decimal import Decimal
            return Decimal(s)
        except Exception:
            self.log.err("[err]Angka desimal tidak valid.[/err]")
            return current

    # ---------- Helper run di thread ----------
    def _bg(self, target: Callable, name="task"):
        t = threading.Thread(target=target, name=name, daemon=True)
        t.start()

    # ---------- Actions ----------
    def run_aio(self) -> None:
        self.log.info("[ok]Menjalankan All-in-One (P1 → P6). Setelah selesai: tidur 24 jam, lalu ulang.[/ok]")

        def task():
            self._stop_flag = False
            while not self._stop_flag:
                try:
                    RUN.run_program_1(RUN.P1_DEFAULT)
                except Exception as e:
                    self.log.err(f"[err]P1 error: {e}[/err]")
                try:
                    RUN.run_program_2(RUN.P2_DEFAULT)
                except Exception as e:
                    self.log.err(f"[err]P2 error: {e}[/err]")
                try:
                    RUN.run_program_3(RUN.P3_DEFAULT)
                except Exception as e:
                    self.log.err(f"[err]P3 error: {e}[/err]")
                try:
                    RUN.run_program_4(RUN.P4_DEFAULT)
                except Exception as e:
                    self.log.err(f"[err]P4 error: {e}[/err]")
                try:
                    RUN.run_program_5(RUN.P5_DEFAULT)
                except Exception as e:
                    self.log.err(f"[err]P5 error: {e}[/err]")
                try:
                    RUN.run_program_6(RUN.P6_DEFAULT)
                except Exception as e:
                    self.log.err(f"[err]P6 error: {e}[/err]")

                if self._stop_flag:
                    break
                self.log.ok("[ok]Selesai 6 program. Tidur 24 jam sebelum siklus berikutnya…[/ok]")
                for s in range(24 * 3600, -1, -1):
                    if self._stop_flag:
                        break
                    if s % 60 == 0:
                        self.log.info(f"⏳ Tidur ~{s//60} menit lagi…")
                    time.sleep(1)

        self._bg(task, "aio")

    def menu_set_defaults(self) -> None:
        items = [
            ("1) Program 1 — Lend & Borrow", self.cfg_p1),
            ("2) Program 2 — Add Domain",    self.cfg_p2),
            ("3) Program 3 — Swap & Earn R2",self.cfg_p3),
            ("4) Program 4 — Brokex Trade",  self.cfg_p4),
            ("5) Program 5 — RwaTrade",      self.cfg_p5),
            ("6) Program 6 — Spout",         self.cfg_p6),
            ("7) Return Main Menu",          self.menu_main),
        ]
        self.menu.set("Set Default Run", items)

    def menu_individual(self) -> None:
        items = [
            ("1) Lend & Borrow", lambda: self._bg(lambda: RUN.run_program_1(RUN.P1_DEFAULT), "p1")),
            ("2) Add Domain",    lambda: self._bg(lambda: RUN.run_program_2(RUN.P2_DEFAULT), "p2")),
            ("3) Swap & Earn R2",lambda: self._bg(lambda: RUN.run_program_3(RUN.P3_DEFAULT), "p3")),
            ("4) Brokex Trade",  lambda: self._bg(lambda: RUN.run_program_4(RUN.P4_DEFAULT), "p4")),
            ("5) RwaTrade",      lambda: self._bg(lambda: RUN.run_program_5(RUN.P5_DEFAULT), "p5")),
            ("6) Spout",         lambda: self._bg(lambda: RUN.run_program_6(RUN.P6_DEFAULT), "p6")),
            ("7) Return Main Menu", self.menu_main),
        ]
        self.menu.set("Individual Run", items)

    def menu_main(self) -> None:
        self.menu.set("Main Menu", self.menu_root)

    # ---------- CONFIG EDITORS ----------
    def cfg_p2(self) -> None:
        RUN.P2_DEFAULT.count = self._prompt_int("P2 — Berapa domain per siklus?", RUN.P2_DEFAULT.count, 1, 100000)
        RUN.P2_DEFAULT.delay_secs = self._prompt_seconds("P2 — Jeda antar domain (detik)", RUN.P2_DEFAULT.delay_secs, 0, 86400)
        self.stats.update()
        self.log.ok("[ok]Default P2 diperbarui.[/ok]")

    def cfg_p4(self) -> None:
        RUN.P4_DEFAULT.runs = self._prompt_int("P4 — Jumlah trade per siklus", RUN.P4_DEFAULT.runs, 1, 100000)
        RUN.P4_DEFAULT.delay_secs = self._prompt_seconds("P4 — Jeda antar trade (detik)", RUN.P4_DEFAULT.delay_secs, 0, 86400)
        self.stats.update()
        self.log.ok("[ok]Default P4 diperbarui.[/ok]")

    def cfg_p5(self) -> None:
        RUN.P5_DEFAULT.runs = self._prompt_int("P5 — Jumlah deposit per siklus", RUN.P5_DEFAULT.runs, 1, 100000)
        RUN.P5_DEFAULT.delay_secs = self._prompt_seconds("P5 — Jeda antar deposit (detik)", RUN.P5_DEFAULT.delay_secs, 0, 86400)
        self.stats.update()
        self.log.ok("[ok]Default P5 diperbarui.[/ok]")

    def cfg_p6(self) -> None:
        RUN.P6_DEFAULT.runs = self._prompt_int("P6 — Jumlah transfer per siklus", RUN.P6_DEFAULT.runs, 1, 100000)
        RUN.P6_DEFAULT.delay_secs = self._prompt_seconds("P6 — Jeda antar transfer (detik)", RUN.P6_DEFAULT.delay_secs, 0, 86400)
        amt = self._prompt_decimal("P6 — Amount per transfer (USDC)", RUN.P6_DEFAULT.amount)
        if amt is not None:
            RUN.P6_DEFAULT.amount = amt
        self.stats.update()
        self.log.ok("[ok]Default P6 diperbarui.[/ok]")

    def cfg_p1(self) -> None:
        try:
            RUN.P1_DEFAULT.repeat = self._prompt_int("P1 — Repeat cycles", RUN.P1_DEFAULT.repeat, 1, 100000)
            RUN.P1_DEFAULT.delay_secs = self._prompt_seconds("P1 — Delay antar tx (detik)", RUN.P1_DEFAULT.delay_secs, 0, 86400)
            self.stats.update()
            self.log.ok("[ok]Default P1 diperbarui.[/ok]")
        except Exception as e:
            self.log.err(f"[err]Gagal update P1: {e}[/err]")

    def cfg_p3(self) -> None:
        RUN.P3_DEFAULT.swap_times = self._prompt_int("P3 — Swap times", RUN.P3_DEFAULT.swap_times, 1, 100000)
        RUN.P3_DEFAULT.delay_secs = self._prompt_seconds("P3 — Delay antar aksi (detik)", RUN.P3_DEFAULT.delay_secs, 0, 86400)
        self.stats.update()
        self.log.ok("[ok]Default P3 diperbarui.[/ok]")

    def exit_app(self) -> None:
        self._stop_flag = True
        try:
            self.app.exit()
        except Exception:
            os._exit(0)

    # ---------- Run ----------
    def run(self) -> None:
        # sanity singkat
        if not os.getenv("PRIVATE_KEY", RUN.PRIVATE_KEY or "").strip():
            self.log.err("[err]PRIVATE_KEY kosong di .env[/err]")
        self.app.run()


# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    RunnerApp().run()
