#!/usr/bin/env python3
"""
Buni for Windows v1.2.0
Claude Code companion – pixel-art rabbit mascot
https://github.com/EloyYang/buni
"""
import tkinter as tk
from tkinter import simpledialog
import threading
import json, time, os, sys, math, glob, random, re
import ctypes, datetime
from pathlib import Path

# ── Pixel unit (matches macOS p = 6.5)
P = 6.5

# ── Window geometry
WIN_W, WIN_H = 340, 240
CHAR_CX      = WIN_W - 52    # character center-X
CHAR_CY      = WIN_H - 80    # character center-Y
SLOT_STEP    = WIN_H + 8     # vertical spacing between session slots

# ── Transparent key color
TRANSP = '#010101'

# ── Character palettes: (body, ear, nose, extras_dict)
#    extras keys: 'brow' (hex color), 'blush' (bool)
CHARACTERS = {
    'rabbit':       ('#E8E8F0', '#F3B8C7', '#E09090', {}),
    'brownRabbit':  ('#9A6633', '#C47844', '#C47844', {'brow': '#35180A'}),
    'pinkRabbit':   ('#FAC7E0', '#FFEAF5', '#F25999', {}),
    'orangeRabbit': ('#F28520', '#FFD199', '#FFE6CC', {}),
    'yellowRabbit': ('#F5DB38', '#FFF5B8', '#FFF2BF', {'blush': True}),
    'greenRabbit':  ('#73CC61', '#C7F2AD', '#D1F2C7', {}),
}
CHAR_DISPLAY_NAMES = {
    'rabbit':       '부니 (흰토끼)',
    'brownRabbit':  '두니 (갈색토끼)',
    'pinkRabbit':   '푸니 (핑크토끼)',
    'orangeRabbit': '주니 (주황토끼)',
    'yellowRabbit': '누니 (노란토끼)',
    'greenRabbit':  '우니 (연두토끼)',
}

# ── Tool classification: read tools → toolRead state
READ_TOOLS = {'read', 'glob', 'grep', 'ls', 'webfetch', 'websearch', 'todoread'}

# ── Laptop colors (from LaptopView.swift)
LAP_SILVER = '#C2C2CC'  # silverCol rgb(0.76,0.76,0.80)
LAP_HI     = '#E0E0EB'  # silverHi  rgb(0.88,0.88,0.92)
LAP_DARK   = '#808089'  # silverDark rgb(0.50,0.50,0.54)
LAP_MID    = '#A3A3AD'  # silverMid  rgb(0.64,0.64,0.68)
LAP_APPLE  = '#EBEBF2'  # appleCol   rgb(0.92,0.92,0.95)

# ── Document colors (from DocumentView.swift)
DOC_PAPER  = '#EDE3C7'  # paperCol  rgb(0.93,0.89,0.78)
DOC_DARK   = '#CCC1A6'  # paperDark rgb(0.80,0.76,0.65)
DOC_LINE_H = '#8C8069'  # lineHeavy rgb(0.55,0.50,0.42)
DOC_LINE_L = '#9E9078'  # lineLight (lighter)
TAB_PINK   = '#FA6699'
TAB_YELLOW = '#FAD633'
TAB_GREEN  = '#47BF59'

# ── Paths
_TEMP      = Path(os.environ.get('TEMP', os.environ.get('TMP', 'C:/temp')))
STATE_FILE = Path.home() / 'AppData' / 'Roaming' / 'Buni' / 'state.json'

# ── Windows API for click-through transparent window
_u32              = ctypes.windll.user32
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020


def _get_hwnd(widget: tk.Widget) -> int:
    return _u32.GetParent(widget.winfo_id())


def _set_click_through(hwnd: int, enable: bool) -> None:
    style = _u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if enable:
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
    else:
        style = (style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT
    _u32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


# ══════════════════════════════════════════════════════════════
class PersistenceManager:
    """JSON-backed key-value store (character, memo, window position)."""

    def __init__(self):
        self._data: dict = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            if STATE_FILE.exists():
                self._data = json.loads(
                    STATE_FILE.read_text(encoding='utf-8'))
        except Exception:
            self._data = {}

    def save(self):
        try:
            with self._lock:
                STATE_FILE.write_text(
                    json.dumps(self._data, indent=2, ensure_ascii=False),
                    encoding='utf-8')
        except Exception:
            pass

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value
        self.save()

    def remove(self, key):
        with self._lock:
            self._data.pop(key, None)
        self.save()


# ══════════════════════════════════════════════════════════════
class SessionWindow:
    """One Toplevel window per active Claude session."""

    def __init__(self, manager: 'BuniManager', session_id: str, slot: int,
                 event_file: Path, persist: PersistenceManager):
        self.manager    = manager
        self.session_id = session_id
        self.slot       = slot
        self.event_file = event_file
        self.persist    = persist

        # ── Toplevel
        self.win = tk.Toplevel(manager.root)
        self._setup_window()
        self.cv = tk.Canvas(self.win, width=WIN_W, height=WIN_H,
                            bg=TRANSP, highlightthickness=0)
        self.cv.pack()

        # ── Character & memo
        self.character: str = self._load_character()
        self.memo:      str = self._load_memo()

        # ── Body/arm animation floats
        self.body_dy  = 0.0;  self.body_dx  = 0.0
        self.larm_dx  = 0.0;  self.larm_dy  = 0.0
        self.rarm_dx  = 0.0;  self.rarm_dy  = 0.0

        # ── Laptop typing state
        self.show_laptop  = False
        self.laptop_phase = False

        # ── Document reading state
        self.show_reading = False
        self._reading_step = 0
        self.throw_dx  = 0.0;  self.throw_dy = 0.0
        self.doc_visible  = True

        # ── Eyes
        self.blinking   = False
        self.wide_eyes  = False

        # ── App state
        self.state          = 'idle'
        self.msg: str | None = None
        self.perm_id: str | None   = None
        self.perm_cmd: str | None  = None
        self.always_approve = False

        # ── Usage
        self._usage               = 0.0
        self._session_start: datetime.datetime | None = None
        self._monthly_tokens: int = 0

        # ── After handles
        self._laptop_job   = None
        self._reading_job  = None
        self._blink_job    = None
        self._idle_job     = None
        self._perm_win: tk.Toplevel | None = None
        self._destroyed    = False

        # ── File monitoring
        self._file_offset = 0
        self._init_file_offset()

        # ── HWND (after window is mapped)
        self._hwnd: int | None = None
        self.win.after(300, self._init_hwnd)

        # ── Position & initial draw
        self._position_window()
        self._draw()

        # ── Bindings
        self._build_menu()
        self.cv.bind('<Button-3>',        self._show_menu)
        self.cv.bind('<Double-Button-1>', lambda _: self._open_claude())
        self.cv.bind('<ButtonPress-1>',   self._drag_press)
        self.cv.bind('<B1-Motion>',       self._drag_motion)
        self.cv.bind('<ButtonRelease-1>', self._drag_release)
        self._drag_start: tuple | None = None

        # ── Start
        self._apply_state('ready')
        self._schedule_blink()
        self._schedule_idle_hop()
        self._tick_bar_refresh()

    # ── Persistence ───────────────────────────────────────────

    def _load_character(self) -> str:
        char = (self.persist.get(f'character.session.{self.session_id}') or
                self.persist.get(f'character.slot.{self.slot}') or 'rabbit')
        return char if char in CHARACTERS else 'rabbit'

    def _load_memo(self) -> str:
        return (self.persist.get(f'memo.session.{self.session_id}') or
                self.persist.get(f'memo.slot.{self.slot}') or '')

    def _save_character(self):
        self.persist.set(f'character.session.{self.session_id}', self.character)
        self.persist.set(f'character.slot.{self.slot}', self.character)

    def _save_memo(self):
        ks = f'memo.session.{self.session_id}'
        kl = f'memo.slot.{self.slot}'
        if self.memo:
            self.persist.set(ks, self.memo)
            self.persist.set(kl, self.memo)
        else:
            self.persist.remove(ks)
            self.persist.remove(kl)

    # ── Window setup ──────────────────────────────────────────

    def _setup_window(self):
        w = self.win
        w.overrideredirect(True)
        w.wm_attributes('-topmost', True)
        w.wm_attributes('-transparentcolor', TRANSP)
        w.config(bg=TRANSP)
        w.resizable(False, False)
        w.title(f'Buni-{self.slot}')

    def _position_window(self):
        sw = self.win.winfo_screenwidth()
        if self.slot == 0:
            saved = self.persist.get('window_pos')
            if saved and isinstance(saved, (list, tuple)) and len(saved) == 2:
                try:
                    x, y = int(saved[0]), int(saved[1])
                    self.win.geometry(f'{WIN_W}x{WIN_H}+{x}+{y}')
                    return
                except Exception:
                    pass
        # Top-right corner, slots stack downward
        x = sw - WIN_W - 10
        y = 50 + self.slot * SLOT_STEP
        self.win.geometry(f'{WIN_W}x{WIN_H}+{x}+{y}')

    def _init_hwnd(self):
        try:
            self._hwnd = _get_hwnd(self.win)
            _set_click_through(self._hwnd, True)
            self.cv.bind('<Enter>', lambda _: self._on_hover(True))
            self.cv.bind('<Leave>', lambda _: self._on_hover(False))
        except Exception:
            pass

    def _on_hover(self, entering: bool):
        if self._hwnd:
            _set_click_through(self._hwnd, not entering)

    # ── Drag ─────────────────────────────────────────────────

    def _drag_press(self, e: tk.Event):
        self._drag_start = (e.x_root, e.y_root,
                            self.win.winfo_x(), self.win.winfo_y())
        if self._hwnd:
            _set_click_through(self._hwnd, False)

    def _drag_motion(self, e: tk.Event):
        if not self._drag_start:
            return
        sx, sy, wx, wy = self._drag_start
        self.win.geometry(f'+{wx + e.x_root - sx}+{wy + e.y_root - sy}')

    def _drag_release(self, _e: tk.Event):
        self._drag_start = None
        if self._hwnd:
            _set_click_through(self._hwnd, True)
        if self.slot == 0:
            self.persist.set('window_pos',
                             [self.win.winfo_x(), self.win.winfo_y()])

    # ── Drawing helpers ───────────────────────────────────────

    def _rect(self, ox: float, oy: float, w: float, h: float,
              color: str, tag: str = 'char') -> None:
        """Pixel block at character-center offset (body_dx/dy applied)."""
        x = CHAR_CX + ox + self.body_dx
        y = CHAR_CY + oy + self.body_dy
        self.cv.create_rectangle(x - w*P/2, y - h*P/2,
                                  x + w*P/2, y + h*P/2,
                                  fill=color, outline='', tags=tag)

    def _rounded_rect(self, x0, y0, x1, y1, r, fill, outline, tag='misc'):
        pts = [x0+r, y0,  x1-r, y0,  x1,  y0,   x1,  y0+r,
               x1,  y1-r, x1,  y1,   x1-r, y1,  x0+r, y1,
               x0,  y1,   x0,  y1-r, x0,  y0+r, x0,  y0]
        self.cv.create_polygon(pts, smooth=True,
                                fill=fill, outline=outline, width=1, tags=tag)

    # ── Full redraw (draw order matches macOS z-order) ────────

    def _draw(self):
        if self._destroyed:
            return
        self.cv.delete('all')
        # 1. Speech bubble (behind everything)
        self._draw_bubble()
        # 2. Paper pile (far left, background)
        if self.show_reading:
            self._draw_doc_pile()
        # 3. Ears (behind head)
        self._draw_ears()
        # 4. Body + arms
        self._draw_body_arms()
        # 5. Laptop (on top of arms, below head)
        if self.show_laptop:
            self._draw_laptop()
        # 6. Feet
        self._draw_feet()
        # 7. Held document (in front of body, behind head)
        if self.show_reading and self.doc_visible:
            self._draw_held_doc()
        # 8. Head (topmost character layer)
        self._draw_head()
        # 9. Usage bar
        self._draw_bar()
        # 10. Memo tag (above ears)
        self._draw_memo()

    # ── Character parts ───────────────────────────────────────

    def _draw_ears(self):
        body, ear, *_ = CHARACTERS[self.character]
        self._rect(-P*1.6, -P*3.5,        1.6, 3.4, body)
        self._rect(-P*1.6, -P*3.5-P*0.1,  0.8, 2.7, ear)
        self._rect( P*1.6, -P*3.5,        1.6, 3.4, body)
        self._rect( P*1.6, -P*3.5-P*0.1,  0.8, 2.7, ear)

    def _draw_body_arms(self):
        body, ear, nose, extras = CHARACTERS[self.character]
        # Body
        self._rect(0, P*1.5, 4.5, 2.5, body)
        # Arms (with dark outline when holding laptop/doc)
        lx = -P*2.65 + self.larm_dx;  ly = P*1.1 + self.larm_dy
        rx =  P*2.65 + self.rarm_dx;  ry = P*1.1 + self.rarm_dy
        if self.show_laptop or self.show_reading:
            self._rect(lx, ly, 1.9, 1.2, '#3A3A3A')   # outline
            self._rect(rx, ry, 1.9, 1.2, '#3A3A3A')
        self._rect(lx, ly, 1.5, 0.9, body)
        self._rect(rx, ry, 1.5, 0.9, body)

    def _draw_feet(self):
        body = CHARACTERS[self.character][0]
        self._rect(-P*1.2, P*2.9, 1.5, 0.9, body)
        self._rect( P*1.2, P*2.9, 1.5, 0.9, body)

    def _draw_head(self):
        body, ear, nose, extras = CHARACTERS[self.character]
        # Head
        self._rect(0, -P*0.8, 5.5, 2.5, body)
        # Eyebrows + stubble (두니 only)
        if 'brow' in extras:
            brow = extras['brow']
            self._rect(-P*1.45, -P*1.35, 0.95, 0.24, brow)
            self._rect( P*1.45, -P*1.35, 0.95, 0.24, brow)
            self._rect(-P*0.85, -P*0.10, 0.20, 0.20, brow)
            self._rect( P*0.85, -P*0.10, 0.20, 0.20, brow)
        # Blush (누니 only)
        if extras.get('blush'):
            self._rect(-P*1.85, -P*0.15, 0.70, 0.40, '#F5B06E')
            self._rect( P*1.85, -P*0.15, 0.70, 0.40, '#F5B06E')
        # Eyes
        ey = -P*0.9
        if self.blinking:    eh = 0.12
        elif self.wide_eyes: eh = 1.10
        else:                eh = 0.75
        self._rect(-P*1.4, ey, 0.65, eh, '#000000')
        self._rect( P*1.4, ey, 0.65, eh, '#000000')
        # Nose
        self._rect(0, -P*0.25, 0.55, 0.40, nose)

    # ── Laptop ────────────────────────────────────────────────

    def _draw_laptop(self):
        """MacBook on character's lap — positions from LaptopView.swift."""
        cx = CHAR_CX + self.body_dx
        cy = CHAR_CY + self.body_dy

        def r(oy, w, h, color):
            y = cy + P * oy
            self.cv.create_rectangle(cx - P*w/2, y - P*h/2,
                                      cx + P*w/2, y + P*h/2,
                                      fill=color, outline='', tags='char')

        r(1.48, 3.15, 2.15, LAP_SILVER)   # Lid back
        r(0.41, 3.15, 0.17, LAP_HI)       # Lid top highlight
        r(2.64, 3.50, 0.20, LAP_DARK)     # Hinge
        r(2.90, 3.80, 0.44, LAP_MID)      # Keyboard base
        r(3.13, 3.80, 0.16, LAP_DARK)     # Keyboard front thickness
        r(2.82, 3.10, 0.13, '#909099')    # Key hint
        r(3.02, 1.00, 0.22, '#9090A0')    # Trackpad
        # Apple logo (simplified)
        lx = cx; ly = cy + P*1.42
        self.cv.create_rectangle(lx - P*0.35, ly - P*0.55,
                                  lx + P*0.35, ly + P*0.40,
                                  fill=LAP_APPLE, outline='', tags='char')

    # ── Document ──────────────────────────────────────────────

    def _draw_doc_pile(self):
        """Paper pile on the left — static, behind character."""
        pile_cx = CHAR_CX + self.body_dx - P*5.4
        pile_cy = CHAR_CY + self.body_dy + P*2.55

        def r(ox, oy, w, h, color):
            x = pile_cx + ox*P;  y = pile_cy + oy*P
            self.cv.create_rectangle(x - w*P/2, y - h*P/2,
                                      x + w*P/2, y + h*P/2,
                                      fill=color, outline='', tags='char')

        r(0.12,  0.84, 2.85, 0.26, DOC_DARK)    # shadow
        r(0,    -0.74, 2.55, 1.45, DOC_PAPER)   # pile body
        r(0,    -1.22, 1.90, 0.13, DOC_LINE_H)
        r(0,    -1.04, 1.60, 0.10, DOC_LINE_L)
        r(0,    -0.88, 1.90, 0.10, DOC_LINE_L)
        r(0,    -0.56, 1.90, 0.10, DOC_LINE_L)
        r(0,    -0.03, 2.55, 0.12, DOC_DARK)    # thickness lines
        r(0,     0.11, 2.55, 0.12, DOC_DARK)
        r(1.28, -0.90, 0.26, 0.52, TAB_PINK)    # post-it tabs
        r(1.28, -0.36, 0.26, 0.46, TAB_YELLOW)
        r(1.28,  0.14, 0.26, 0.44, TAB_GREEN)

    def _draw_held_doc(self):
        """Document the character is holding — affected by throw offset."""
        doc_cx = CHAR_CX + self.body_dx + self.throw_dx
        doc_cy = CHAR_CY + self.body_dy + self.throw_dy

        def r(oy, w, h, color):
            y = doc_cy + P * oy
            self.cv.create_rectangle(doc_cx - P*w/2, y - P*h/2,
                                      doc_cx + P*w/2, y + P*h/2,
                                      fill=color, outline='', tags='char')

        r(1.90, 3.2, 2.80, DOC_DARK)    # shadow
        r(1.80, 3.0, 2.80, DOC_PAPER)   # paper main
        r(0.55, 3.0, 0.13, DOC_LINE_H)  # top separator
        r(0.78, 1.85, 0.25, DOC_LINE_H) # title
        r(1.06, 1.30, 0.16, DOC_LINE_L)
        r(1.35, 2.55, 0.13, DOC_LINE_L) # body lines
        r(1.55, 2.55, 0.13, DOC_LINE_L)
        r(1.75, 2.55, 0.13, DOC_LINE_L)
        r(1.95, 2.10, 0.13, DOC_LINE_L)
        r(2.36, 2.55, 0.13, DOC_LINE_L)
        r(2.55, 1.80, 0.13, DOC_LINE_L)
        # Corner fold
        corner_x = doc_cx + P*1.29
        corner_y = doc_cy + P*0.47
        self.cv.create_rectangle(corner_x - P*0.21, corner_y - P*0.21,
                                  corner_x + P*0.21, corner_y + P*0.21,
                                  fill=DOC_DARK, outline='', tags='char')

    # ── Speech bubble ─────────────────────────────────────────

    def _draw_bubble(self):
        if not self.msg:
            return
        bx  = CHAR_CX - P*5 + self.body_dx
        by  = CHAR_CY - P*3.5 + self.body_dy
        pad = 10
        font = ('Malgun Gothic', 10)
        tmp = self.cv.create_text(0, 0, text=self.msg, font=font)
        bb  = self.cv.bbox(tmp); self.cv.delete(tmp)
        tw  = (bb[2] - bb[0]) if bb else 60
        bw  = tw + pad*2;  bh = 28;  r = 8
        x0  = bx - bw;    x1 = bx
        y0  = by - bh/2;  y1 = by + bh/2
        self._rounded_rect(x0, y0, x1, y1, r, 'white', '#cccccc', 'bubble')
        self.cv.create_polygon(x1-2, by-5, x1+9, by, x1-2, by+5,
                                fill='white', outline='', tags='bubble')
        self.cv.create_text(x0+pad, (y0+y1)/2, text=self.msg,
                             anchor='w', font=font, fill='#222222', tags='bubble')

    # ── Memo tag ──────────────────────────────────────────────

    def _draw_memo(self):
        if not self.memo:
            return
        cx  = CHAR_CX + self.body_dx
        cy  = CHAR_CY + self.body_dy - P*5.2   # above the ears
        font = ('Malgun Gothic', 9, 'bold')
        self.cv.create_text(cx+1, cy+1, text=self.memo, anchor='center',
                             font=font, fill='#000000', tags='memo')
        self.cv.create_text(cx,   cy,   text=self.memo, anchor='center',
                             font=font, fill='#FFFFFF', tags='memo')

    # ── Usage bar ─────────────────────────────────────────────

    def _draw_bar(self):
        if self.state == 'idle':
            return
        SEG = 10; GAP = 2; BW = 1.5; SH = 9
        bx = CHAR_CX - P*3.3
        w  = P*6.6
        sw = (w - GAP*(SEG-1)) / SEG
        filled = max(0, min(SEG, int(self._usage * SEG + 0.5)))

        feet_y  = CHAR_CY + P*3.35
        lv_y    = feet_y + 8
        bar_y   = lv_y + 14
        label_y = bar_y + SH + BW + 9

        self._rounded_rect(bx-5, lv_y-8, bx+w+5, label_y+8, 6, '#1E1E1E', '', 'bar')

        self.cv.create_text(bx, lv_y,
                             text=f'★ Lv.{self._monthly_tokens // 500_000 + 1}',
                             anchor='w', font=('Consolas', 7, 'bold'),
                             fill='#F2CC25', tags='bar')

        self._rounded_rect(bx-BW, bar_y-BW, bx+w+BW, bar_y+SH+BW, 3, '', '#666666', 'bar')

        for i in range(SEG):
            ratio = (i+1)/SEG
            fc = '#4DDA59' if ratio <= 0.50 else '#F2CC25' if ratio <= 0.75 else '#F24D33'
            sx = bx + i*(sw+GAP)
            if i < filled:
                self.cv.create_rectangle(sx, bar_y, sx+sw, bar_y+SH,
                                          fill=fc, outline='', tags='bar')
                self.cv.create_rectangle(sx, bar_y, sx+sw, bar_y+2,
                                          fill='#FFFFFF', outline='', tags='bar')

        self.cv.create_text(bx, label_y, text=f'{round(self._usage*100)}%',
                             anchor='w', font=('Consolas', 7),
                             fill='#AAAAAA', tags='bar')
        rst = self._reset_time_str()
        if rst:
            self.cv.create_text(bx+w, label_y, text=f'↺ {rst}',
                                 anchor='e', font=('Consolas', 7),
                                 fill='#AAAAAA', tags='bar')

    def _reset_time_str(self) -> str:
        if self._session_start is None:
            return ''
        reset_at = self._session_start + datetime.timedelta(hours=5)
        diff = int((reset_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
        if diff <= 0:
            return ''
        h = diff // 3600; m = (diff % 3600) // 60
        return f'{h}:{m:02d}' if h > 0 else f'{m}m'

    def _tick_bar_refresh(self):
        if self._destroyed:
            return
        if self.state != 'idle':
            self._draw()
        self.win.after(30_000, self._tick_bar_refresh)

    # ── Blink ─────────────────────────────────────────────────

    def _schedule_blink(self):
        if self._destroyed:
            return
        self._blink_job = self.win.after(random.randint(2500, 6000), self._do_blink)

    def _do_blink(self):
        if self._destroyed:
            return
        self.blinking = True;  self._draw()
        self.win.after(130, self._end_blink)

    def _end_blink(self):
        if self._destroyed:
            return
        self.blinking = False; self._draw()
        self._schedule_blink()

    # ── Idle hop ──────────────────────────────────────────────

    def _schedule_idle_hop(self):
        if self._destroyed:
            return
        self._idle_job = self.win.after(random.randint(5000, 14000), self._do_idle_hop)

    def _do_idle_hop(self):
        if self._destroyed:
            return
        if self.state != 'ready':
            self._schedule_idle_hop(); return
        if random.random() < 0.5:
            self._hop_anim(on_done=self._schedule_idle_hop)
        else:
            self._ear_anim(on_done=self._schedule_idle_hop)

    def _hop_anim(self, on_done=None):
        frames = [0, -P*0.8, -P*1.5, -P*1.8, -P*1.5, -P*0.8, 0]
        def step(i=0):
            if self._destroyed: return
            if i >= len(frames):
                self.body_dy = 0; self._draw()
                if on_done: on_done(); return
            self.body_dy = frames[i]; self._draw()
            self.win.after(40, lambda: step(i+1))
        step()

    def _ear_anim(self, on_done=None):
        frames = [0, P*0.5, P*1.0, P*0.5, 0, -P*0.5, 0]
        def step(i=0):
            if self._destroyed: return
            if i >= len(frames):
                self.body_dx = 0; self._draw()
                if on_done: on_done(); return
            self.body_dx = frames[i]; self._draw()
            self.win.after(60, lambda: step(i+1))
        step()

    def _bounce(self, high: bool = False):
        amp = -P*2.5 if high else -P*2.0
        frames = [0, P*0.5*amp/(-P*2), amp*0.8, amp, amp*0.8, P*0.5*amp/(-P*2), 0]
        frames = [0, amp*0.35, amp*0.80, amp, amp*0.80, amp*0.35, 0]
        def step(i=0):
            if self._destroyed: return
            if i >= len(frames):
                self.body_dy = 0; self._draw(); return
            self.body_dy = frames[i]; self._draw()
            self.win.after(30, lambda: step(i+1))
        step()

    # ── Laptop typing ─────────────────────────────────────────

    def _start_laptop(self):
        if self.show_laptop:
            return
        self.larm_dx =  P*1.55; self.rarm_dx = -P*1.55
        self.larm_dy =  P*1.00; self.rarm_dy =  P*1.00
        self.show_laptop  = True
        self.laptop_phase = False
        self._draw()
        self._tick_laptop()

    def _tick_laptop(self):
        if self._destroyed:
            return
        if self.state not in ('thinking', 'toolUse'):
            self._laptop_job = None; return
        self.laptop_phase = not self.laptop_phase
        base = P*1.00; swing = P*0.60
        if self.laptop_phase:
            self.larm_dy = base - swing; self.rarm_dy = base + swing
        else:
            self.larm_dy = base + swing; self.rarm_dy = base - swing
        self._draw()
        self._laptop_job = self.win.after(360, self._tick_laptop)

    def _stop_laptop(self):
        if self._laptop_job:
            self.win.after_cancel(self._laptop_job); self._laptop_job = None
        self.show_laptop = False
        if not self.show_reading:
            self.larm_dx = self.larm_dy = 0.0
            self.rarm_dx = self.rarm_dy = 0.0

    # ── Document reading ──────────────────────────────────────

    def _start_reading(self):
        if self.show_reading:
            return
        self.larm_dx =  P*1.55; self.rarm_dx = -P*1.55
        self.larm_dy =  P*0.25; self.rarm_dy =  P*0.25
        self.show_reading = True
        self.throw_dx = 0.0; self.throw_dy = 0.0
        self.doc_visible  = True
        self._reading_step = 0
        self._draw()
        self._step_reading()

    def _step_reading(self):
        if self._destroyed or self.state != 'toolRead':
            return
        self._reading_step += 1
        if self._reading_step % 3 == 0:
            self._throw_and_replace()
        else:
            phase = (self._reading_step % 2) == 0
            self.larm_dy = P*0.18 if phase else P*0.30
            self.rarm_dy = P*0.30 if phase else P*0.18
            self._draw()
            self._reading_job = self.win.after(1300, self._step_reading)

    def _throw_and_replace(self):
        if self._destroyed or self.state != 'toolRead':
            return
        # Arms up for the throw
        self.larm_dy = -P*0.30; self.rarm_dy = -P*0.30
        self.larm_dx =  P*1.80; self.rarm_dx = -P*1.80

        # Step through throw offset
        throw_frames = [(P*1.5, -P*1.0), (P*3.0, -P*2.0), (P*4.0, -P*3.0)]

        def step_throw(i=0):
            if self._destroyed: return
            if i < len(throw_frames):
                self.throw_dx, self.throw_dy = throw_frames[i]
                self._draw()
                self.win.after(65, lambda: step_throw(i+1))
            else:
                # Doc thrown away — hide and snap back
                self.doc_visible = False
                self.throw_dx = 0.0; self.throw_dy = 0.0
                self._draw()
                self.win.after(300, self._replace_doc)

        step_throw()

    def _replace_doc(self):
        if self._destroyed or self.state != 'toolRead':
            return
        self.doc_visible = True
        self.larm_dy =  P*0.25; self.rarm_dy =  P*0.25
        self.larm_dx =  P*1.55; self.rarm_dx = -P*1.55
        self._draw()
        self._reading_job = self.win.after(400, self._step_reading)

    def _stop_reading(self):
        if self._reading_job:
            self.win.after_cancel(self._reading_job); self._reading_job = None
        self.show_reading = False
        self.throw_dx = 0.0; self.throw_dy = 0.0
        self.doc_visible  = True
        if not self.show_laptop:
            self.larm_dx = self.larm_dy = 0.0
            self.rarm_dx = self.rarm_dy = 0.0

    # ── State machine ─────────────────────────────────────────

    def _apply_state(self, new_state: str, *, tool=None, notif=None,
                     perm_cmd=None, perm_id=None):
        if not self._destroyed:
            self.win.after(0, lambda: self._do_apply(
                new_state, tool, notif, perm_cmd, perm_id))

    def _do_apply(self, new_state, tool, notif, perm_cmd, perm_id):
        if self._destroyed:
            return
        self.state = new_state
        self.wide_eyes = False

        # Stop animations that are no longer relevant
        if new_state not in ('thinking', 'toolUse'):
            self._stop_laptop()
        if new_state != 'toolRead':
            self._stop_reading()

        if new_state == 'idle':
            self.msg = None
            self._draw()

        elif new_state == 'thinking':
            self.msg = '코딩중'
            self._start_laptop()
            self._draw()

        elif new_state == 'toolUse':
            self.msg = tool or '작업 중...'
            self._start_laptop()
            self._draw()

        elif new_state == 'toolRead':
            self.msg = tool or '읽는 중...'
            self._start_reading()
            self._draw()

        elif new_state == 'notification':
            self.msg = notif
            self._draw()
            self._bounce()
            self.win.after(5000, lambda: self._clear_msg_if(notif))

        elif new_state == 'permission':
            self.wide_eyes = True
            self.msg = None
            self.perm_cmd = perm_cmd
            self.perm_id  = perm_id
            self._draw()
            self._show_perm_popup()

        elif new_state == 'completed':
            self.msg = None
            self.wide_eyes = True
            self._bounce(high=True)
            self._draw()
            self.win.after(2000, lambda: (
                self._apply_state('ready') if self.state == 'completed' else None))

        elif new_state == 'ready':
            self.msg = None
            self._draw()

    def _clear_msg_if(self, old_msg):
        if not self._destroyed and self.msg == old_msg:
            self.msg = None; self._draw()

    # ── Permission popup ──────────────────────────────────────

    def _show_perm_popup(self):
        if self._perm_win and self._perm_win.winfo_exists():
            self._perm_win.destroy()

        win = tk.Toplevel(self.win)
        self._perm_win = win
        win.overrideredirect(True)
        win.wm_attributes('-topmost', True)
        win.config(bg='white')

        rx = self.win.winfo_x(); ry = self.win.winfo_y()
        win.geometry(f'230x160+{rx-235}+{ry+20}')

        tk.Label(win, text='🔐 실행 허용?', font=('Consolas', 11, 'bold'),
                 bg='white').pack(anchor='w', padx=12, pady=(10, 2))

        cmd_box = tk.Text(win, height=4, font=('Consolas', 9),
                          bg='#F0F0F0', relief='flat', wrap='word')
        cmd_box.insert('1.0', self.perm_cmd or '')
        cmd_box.config(state='disabled')
        cmd_box.pack(fill='x', padx=12, pady=4)

        btn_f = tk.Frame(win, bg='white')
        btn_f.pack(padx=12, pady=(4, 10))

        def btn(text, fg, action):
            tk.Button(btn_f, text=text, font=('Consolas', 9, 'bold'),
                      fg='white', bg=fg, relief='flat', padx=8, pady=4,
                      command=lambda: self._decide(action)).pack(side='left', padx=3)

        btn('거부',     '#D93A2F', 'deny')
        btn('허용',     '#2DB357', 'approve')
        btn('전체 허용', '#3D7FE0', 'approve_all')

    def _decide(self, action: str):
        if self._perm_win and self._perm_win.winfo_exists():
            self._perm_win.destroy()
        pid = self.perm_id
        if not pid:
            return
        if action == 'approve_all':
            self.always_approve = True
            action = 'approve'
        decision = 'approve' if action == 'approve' else 'deny'
        try:
            (_TEMP / f'claude-companion-decision-{pid}').write_text(decision)
        except Exception:
            pass
        self.perm_id = None
        self._apply_state('thinking')

    # ── Context menu ──────────────────────────────────────────

    def _build_menu(self):
        self._menu = tk.Menu(self.win, tearoff=0)
        self._menu.add_command(label='숨기기',  command=self.manager.hide_all)
        self._menu.add_command(label='Claude 열기', command=self._open_claude)
        self._menu.add_separator()

        char_menu = tk.Menu(self._menu, tearoff=0)
        for cid, name in CHAR_DISPLAY_NAMES.items():
            char_menu.add_command(label=name,
                                   command=lambda c=cid: self._set_character(c))
        self._menu.add_cascade(label='캐릭터 변경', menu=char_menu)

        self._menu.add_separator()
        label = '메모 추가...' if not self.memo else '메모 편집...'
        self._menu.add_command(label=label, command=self._edit_memo)
        if self.memo:
            self._menu.add_command(label='메모 지우기', command=self._clear_memo)

        self._menu.add_separator()
        self._menu.add_command(label='위치 초기화', command=self._reset_position)
        self._menu.add_separator()
        self._menu.add_command(label='종료', command=self.manager.quit)

    def _show_menu(self, e: tk.Event):
        self._build_menu()
        try:
            self._menu.tk_popup(e.x_root, e.y_root)
        finally:
            self._menu.grab_release()

    def _open_claude(self):
        try:
            os.startfile('claude')
        except Exception:
            pass

    def _set_character(self, char_id: str):
        self.character = char_id
        self._save_character()
        self._draw()

    def _edit_memo(self):
        result = simpledialog.askstring(
            '메모 설정',
            '이 캐릭터의 메모를 입력하세요:\n(빈칸으로 두면 메모가 삭제됩니다)',
            initialvalue=self.memo, parent=self.win)
        if result is not None:
            self.memo = result.strip()
            self._save_memo()
            self._draw()

    def _clear_memo(self):
        self.memo = ''
        self._save_memo()
        self._draw()

    def _reset_position(self):
        if self.slot == 0:
            self.persist.remove('window_pos')
        self._position_window()

    # ── Usage ─────────────────────────────────────────────────

    def set_usage(self, pct: float, session_start_ts=None):
        self._usage = max(0.0, min(1.0, pct / 100.0))
        if session_start_ts:
            try:
                parsed = datetime.datetime.fromisoformat(
                    session_start_ts.replace('Z', '+00:00'))
                if self._session_start is None or parsed < self._session_start:
                    self._session_start = parsed
            except Exception:
                pass
        self._draw()

    def set_monthly_tokens(self, tokens: int):
        self._monthly_tokens = tokens
        self._draw()

    # ── Event file polling ────────────────────────────────────

    def _init_file_offset(self):
        try:
            if self.event_file.exists():
                self._file_offset = self.event_file.stat().st_size
        except Exception:
            pass

    def poll_events(self) -> bool:
        """Read new lines from event file. Returns False if file gone."""
        if self._destroyed:
            return False
        try:
            size = self.event_file.stat().st_size
        except FileNotFoundError:
            return False
        if size <= self._file_offset:
            return True
        try:
            with self.event_file.open('r', encoding='utf-8', errors='replace') as f:
                f.seek(self._file_offset)
                data = f.read()
            self._file_offset = self.event_file.stat().st_size
        except Exception:
            return True
        for line in data.splitlines():
            if line.strip():
                self._handle_event(line)
        return True

    def _handle_event(self, raw: str):
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            return
        t = ev.get('type', '')

        if t == 'tool_use':
            tool_raw  = ev.get('tool', 'tool')
            label     = self._fmt_tool(tool_raw)
            if tool_raw.lower() in READ_TOOLS:
                self._apply_state('toolRead', tool=label)
            else:
                self._apply_state('toolUse',  tool=label)

        elif t == 'tool_done':
            self._apply_state('thinking')

        elif t == 'done':
            self._apply_state('completed')

        elif t == 'notification':
            self._apply_state('notification', notif=ev.get('message', '알림'))

        elif t == 'permission_request':
            pid = ev.get('id');  cmd = ev.get('message', '명령')
            if pid and self.always_approve:
                try:
                    (_TEMP / f'claude-companion-decision-{pid}').write_text('approve')
                except Exception:
                    pass
            elif pid:
                self._apply_state('permission', perm_cmd=cmd, perm_id=pid)

        elif t == 'usage':
            pct = ev.get('percent', 0)
            sts = ev.get('sessionStartTs', None)
            self.win.after(0, lambda p=pct, s=sts: self.set_usage(p, s))

    @staticmethod
    def _fmt_tool(raw: str) -> str:
        return {
            'bash':      '터미널 실행 중',
            'read':      '파일 읽는 중',
            'write':     '파일 쓰는 중',
            'edit':      '파일 수정 중',
            'multiedit': '파일 수정 중',
            'glob':      '파일 검색 중',
            'grep':      '코드 검색 중',
            'ls':        '폴더 탐색 중',
            'websearch': '웹 검색 중',
            'webfetch':  '페이지 읽는 중',
            'todowrite': '할 일 정리 중',
            'todoread':  '할 일 확인 중',
        }.get(raw.lower(), f'{raw} 실행 중')

    # ── Visibility ────────────────────────────────────────────

    def hide(self):
        self.win.withdraw()

    def show(self):
        self.win.deiconify()

    @property
    def is_visible(self) -> bool:
        try:
            return self.win.state() == 'normal'
        except Exception:
            return False

    # ── Cleanup ───────────────────────────────────────────────

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        for job_attr in ('_laptop_job', '_reading_job', '_blink_job', '_idle_job'):
            job = getattr(self, job_attr, None)
            if job:
                try: self.win.after_cancel(job)
                except Exception: pass
        if self._perm_win:
            try: self._perm_win.destroy()
            except Exception: pass
        try: self.win.destroy()
        except Exception: pass


# ══════════════════════════════════════════════════════════════
class BuniManager:
    """Root application — manages multiple SessionWindows."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()   # hidden background window

        self.persist  = PersistenceManager()
        self.sessions: dict[str, SessionWindow] = {}
        self._slot_map: dict[int, str] = {}
        self._is_manually_hidden = False
        self._monthly_tokens = 0
        self._claude_was_running = False

        # Start threads
        threading.Thread(target=self._monitor_loop,      daemon=True).start()
        threading.Thread(target=self._token_loop,        daemon=True).start()

        # Poll sessions on main thread
        self._poll_sessions()

        # System tray
        self._start_tray()

        self.root.mainloop()

    # ── Session management ────────────────────────────────────

    def _next_slot(self) -> int:
        for i in range(20):
            if i not in self._slot_map:
                return i
        return len(self._slot_map)

    def _add_session(self, session_id: str, event_file: Path):
        if session_id in self.sessions:
            return

        slot = self._next_slot()
        self._slot_map[slot] = session_id

        # Pre-assign character if not already stored
        if not self.persist.get(f'character.session.{session_id}'):
            in_use = {sw.character for sw in self.sessions.values()}
            slot_char = self.persist.get(f'character.slot.{slot}')
            if slot_char and slot_char not in in_use and slot_char in CHARACTERS:
                self.persist.set(f'character.session.{session_id}', slot_char)
            else:
                for cid in CHARACTERS:
                    if cid not in in_use:
                        self.persist.set(f'character.session.{session_id}', cid)
                        break

        win = SessionWindow(self, session_id, slot, event_file, self.persist)
        win.set_monthly_tokens(self._monthly_tokens)
        self.sessions[session_id] = win

        if self._is_manually_hidden:
            win.hide()

    def remove_session(self, session_id: str):
        win = self.sessions.pop(session_id, None)
        if win:
            self._slot_map.pop(win.slot, None)
            win.destroy()

    def hide_all(self):
        self._is_manually_hidden = True
        for win in self.sessions.values():
            win.hide()

    def show_all(self):
        self._is_manually_hidden = False
        for win in self.sessions.values():
            win.show()

    def quit(self):
        self.root.quit()
        sys.exit(0)

    # ── Session polling (main thread) ─────────────────────────

    def _poll_sessions(self):
        for sid in list(self.sessions.keys()):
            win = self.sessions.get(sid)
            if win and not win.poll_events():
                # event file gone — remove session
                self.root.after(0, lambda s=sid: self.remove_session(s))
        self.root.after(500, self._poll_sessions)

    # ── File monitor (background thread) ─────────────────────

    def _monitor_loop(self):
        """Detect new/removed event files and Claude process state."""
        while True:
            try:
                pattern = str(_TEMP / 'claude-companion-events-*.jsonl')
                found: dict[str, Path] = {}
                for p in glob.glob(pattern):
                    fp  = Path(p)
                    sid = self._sid_from_file(fp)
                    found[sid] = fp

                # New sessions
                for sid, fp in found.items():
                    if sid not in self.sessions:
                        self.root.after(0, lambda s=sid, f=fp: self._add_session(s, f))

                # Claude process state (for idle detection)
                running = self._is_claude_running()
                if not running and self._claude_was_running:
                    # All sessions go idle
                    self.root.after(0, self._all_sessions_idle)
                elif running and not self._claude_was_running:
                    # Claude started — sessions already created via file detection
                    pass
                self._claude_was_running = running

            except Exception:
                pass
            time.sleep(1.0)

    def _all_sessions_idle(self):
        for win in list(self.sessions.values()):
            win._apply_state('idle')

    @staticmethod
    def _sid_from_file(f: Path) -> str:
        m = re.search(r'claude-companion-events-(.+)\.jsonl$', f.name)
        return m.group(1) if m else f.stem

    @staticmethod
    def _is_claude_running() -> bool:
        try:
            import subprocess
            CREATE_NO_WINDOW = 0x08000000
            out = subprocess.check_output(
                ['tasklist', '/FI', 'IMAGENAME eq node.exe', '/NH'],
                stderr=subprocess.DEVNULL, text=True,
                creationflags=CREATE_NO_WINDOW)
            return 'node.exe' in out.lower()
        except Exception:
            return False

    # ── Monthly token refresh (background thread) ─────────────

    def _token_loop(self):
        while True:
            try:
                total = 0
                projects_dir = Path.home() / '.claude' / 'projects'
                if projects_dir.exists():
                    now = datetime.datetime.now()
                    for jf in projects_dir.rglob('*.jsonl'):
                        try:
                            for line in jf.read_text(
                                    encoding='utf-8', errors='replace').splitlines():
                                if not line.strip():
                                    continue
                                obj = json.loads(line)
                                ts_str = obj.get('timestamp', '')
                                if ts_str:
                                    try:
                                        ts = datetime.datetime.fromisoformat(
                                            ts_str.replace('Z', '+00:00'))
                                        if ts.year != now.year or ts.month != now.month:
                                            continue
                                    except Exception:
                                        continue
                                usage = (obj.get('message', {}) or {}).get('usage', {})
                                total += usage.get('input_tokens', 0)
                                total += usage.get('output_tokens', 0)
                        except Exception:
                            continue
                self._monthly_tokens = total
                self.root.after(0, self._broadcast_tokens)
            except Exception:
                pass
            time.sleep(300)

    def _broadcast_tokens(self):
        for win in self.sessions.values():
            win.set_monthly_tokens(self._monthly_tokens)

    # ── System tray ───────────────────────────────────────────

    def _start_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            return   # pystray/Pillow not installed

        def make_icon():
            img = Image.new('RGB', (32, 32), '#9A6633')
            d = ImageDraw.Draw(img)
            d.ellipse([8, 4, 24, 20], fill='#E8E8F0')
            return img

        def on_toggle(icon, _item):
            self.root.after(0, lambda: (
                self.hide_all()
                if any(w.is_visible for w in self.sessions.values())
                else self.show_all()
            ))

        def on_quit(icon, _item):
            icon.stop()
            self.root.after(0, self.quit)

        icon = pystray.Icon(
            'Buni', make_icon(), 'Buni',
            pystray.Menu(
                pystray.MenuItem('보이기/숨기기', on_toggle),
                pystray.MenuItem('종료', on_quit),
            ))
        threading.Thread(target=icon.run, daemon=True).start()


# ── Entry point ───────────────────────────────────────────────

if __name__ == '__main__':
    BuniManager()
