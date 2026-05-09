import sys, os, json, time, threading, serial, random, math, glob
import cv2

from serial.tools import list_ports                           # Auto-detect ports

from pynput.keyboard import Controller, Key

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton,
    QLineEdit, QStackedWidget, QVBoxLayout, QHBoxLayout,
    QSystemTrayIcon, QMenu, QListWidget,
    QLabel, QSizePolicy, QComboBox                             # QComboBox for port selector
)

from PyQt6.QtCore import (
    Qt, QTimer, QPointF, QEvent,
    QPropertyAnimation, QRect, QRectF,
    QEasingCurve, QPoint, pyqtProperty
)

from PyQt6.QtGui import (
    QColor, QPainter, QImage,
    QPixmap, QIcon, QAction,
    QLinearGradient, QRadialGradient, QPen, QFont,
    QPainterPath, QConicalGradient
)

kb = Controller()

CONFIG = os.path.join(os.getenv("APPDATA"), "holo_system.json")
VIDEO_FOLDER = r"C:\Users\sandr\Documents\2key"


# ---------------- PORT SCANNER ----------------                 

def scan_serial_ports():
    """Scan all available serial ports. Returns list of (device, description, is_arduino)."""
    ports = list(list_ports.comports())
    if not ports:
        return []

    arduino_vids = {
        0x2341, 0x2A03,   # Arduino SA / Arduino.org
        0x1A86,            # CH340 (common clone)
        0x0403,            # FTDI
        0x10C4,            # CP210x (Silicon Labs)
        0x16D0,            # Arduino Mega 2560 R3 (Mega)
        0x239A,            # Adafruit
        0x2886,            # Seeedstudio
        0x1B4F,            # SparkFun
    }

    arduino_keywords = [
        "arduino", "ch340", "ch341", "cp210", "ftdi",
        "usb-serial", "usbserial", "silab", "prolific",
        "acm", "duino"
    ]

    scored = []
    for port in ports:
        desc = (port.description or "").lower()
        mfg  = (port.manufacturer or "").lower()
        is_arduino = port.vid in arduino_vids if port.vid else False

        if not is_arduino:
            for kw in arduino_keywords:
                if kw in desc or kw in mfg:
                    is_arduino = True
                    break

        scored.append((0 if is_arduino else 1, port.device, port.description))

    scored.sort()
    return [(dev, desc, bool(rank == 0)) for rank, dev, desc in scored]


# ---------------- THEMES ----------------

THEMES = {

    # ── VOID / PURPLE ─────────────────────────────────────────────────
    "void":        {"bg": "#0a0014", "a": (160,  80, 255), "b": (255,  80, 200), "c": (0, 255, 200), "star_tint": (200, 180, 255), "pulse_speed": 3.0, "effect": "geometry"},
    "void dark":   {"bg": "#040008", "a": (100,  35, 210), "b": (210,  35, 155), "c": (50, 200, 180), "star_tint": (150, 130, 200), "pulse_speed": 2.5, "effect": "geometry"},
    "void light":  {"bg": "#1e0042", "a": (210, 145, 255), "b": (255, 155, 235), "c": (180, 255, 240), "star_tint": (230, 210, 255), "pulse_speed": 3.5, "effect": "geometry"},
    "amethyst":    {"bg": "#0d001e", "a": (185, 100, 255), "b": (130,  50, 210), "c": (255, 200, 255), "star_tint": (180, 150, 255), "pulse_speed": 2.8, "effect": "geometry"},
    "ultraviolet": {"bg": "#060010", "a": (115,  30, 255), "b": (195,  30, 255), "c": (255, 50, 255), "star_tint": (160, 100, 255), "pulse_speed": 4.0, "effect": "warp"},

    # ── PINK / MAGENTA ────────────────────────────────────────────────
    "pink":        {"bg": "#14000f", "a": (255, 105, 180), "b": (255,  20, 147), "c": (255, 255, 200), "star_tint": (255, 180, 220), "pulse_speed": 3.0, "effect": "petals"},
    "pink dark":   {"bg": "#08000a", "a": (195,  45, 125), "b": (195,   5,  95), "c": (200, 150, 255), "star_tint": (180, 120, 160), "pulse_speed": 2.2, "effect": "petals"},
    "pink light":  {"bg": "#2a001e", "a": (255, 175, 215), "b": (255, 125, 195), "c": (255, 240, 245), "star_tint": (255, 200, 230), "pulse_speed": 3.5, "effect": "petals"},
    "magenta":     {"bg": "#100010", "a": (255,   0, 255), "b": (200,   0, 200), "c": (255, 100, 255), "star_tint": (255, 100, 255), "pulse_speed": 4.5, "effect": "geometry"},
    "sakura":      {"bg": "#180010", "a": (255, 150, 190), "b": (230,  75, 145), "c": (255, 230, 240), "star_tint": (255, 200, 220), "pulse_speed": 2.0, "effect": "paws"},
    "rose":        {"bg": "#120008", "a": (255,  80, 130), "b": (220,  30,  80), "c": (255, 200, 200), "star_tint": (255, 150, 170), "pulse_speed": 3.2, "effect": "petals"},

    # ── RED ───────────────────────────────────────────────────────────
    "red":         {"bg": "#120000", "a": (255,  40,  40), "b": (255, 120, 120), "c": (255, 255, 100), "star_tint": (255, 150, 150), "pulse_speed": 4.0, "effect": "embers"},
    "red dark":    {"bg": "#080000", "a": (175,   8,   8), "b": (195,  55,  55), "c": (200, 100, 50), "star_tint": (150, 80, 80), "pulse_speed": 2.5, "effect": "embers"},
    "crimson":     {"bg": "#0e0000", "a": (220,  20, 60), "b": (175,   0, 25), "c": (255, 50, 100), "star_tint": (200, 100, 120), "pulse_speed": 3.5, "effect": "embers"},
    "coral":       {"bg": "#140600", "a": (255,  95,  70), "b": (255, 155, 100), "c": (255, 255, 200), "star_tint": (255, 200, 180), "pulse_speed": 3.0, "effect": "embers"},

    # ── ORANGE ────────────────────────────────────────────────────────
    "orange":      {"bg": "#140800", "a": (255, 140,   0), "b": (255,  75,   0), "c": (255, 255, 150), "star_tint": (255, 200, 150), "pulse_speed": 3.5, "effect": "embers"},
    "orange dark": {"bg": "#080300", "a": (195,  85,   0), "b": (195,  35,   0), "c": (200, 150, 50), "star_tint": (200, 150, 100), "pulse_speed": 2.8, "effect": "embers"},
    "amber":       {"bg": "#120a00", "a": (255, 180,  50), "b": (255, 120,   0), "c": (255, 255, 200), "star_tint": (255, 220, 150), "pulse_speed": 3.0, "effect": "embers"},
    "sunset":      {"bg": "#140500", "a": (255,  95,  20), "b": (255, 185,  55), "c": (255, 100, 100), "star_tint": (255, 180, 120), "pulse_speed": 2.5, "effect": "embers"},

    # ── GOLD / YELLOW ─────────────────────────────────────────────────
    "gold":        {"bg": "#141000", "a": (255, 215,   0), "b": (255, 168,   0), "c": (255, 255, 255), "star_tint": (255, 240, 150), "pulse_speed": 2.5, "effect": "stars"},
    "gold dark":   {"bg": "#080800", "a": (195, 150,   0), "b": (195, 105,   0), "c": (200, 200, 150), "star_tint": (200, 180, 100), "pulse_speed": 2.0, "effect": "stars"},
    "yellow":      {"bg": "#141400", "a": (255, 255,   0), "b": (205, 205,   0), "c": (255, 255, 200), "star_tint": (255, 255, 150), "pulse_speed": 4.0, "effect": "stars"},
    "lemon":       {"bg": "#101400", "a": (240, 255,  80), "b": (200, 235,   0), "c": (255, 255, 220), "star_tint": (230, 255, 150), "pulse_speed": 3.5, "effect": "stars"},

    # ── GREEN ─────────────────────────────────────────────────────────
    "green":       {"bg": "#00140a", "a": (  0, 255, 120), "b": (120, 255,   0), "c": (200, 255, 200), "star_tint": (150, 255, 180), "pulse_speed": 3.0, "effect": "rain"},
    "green dark":  {"bg": "#000a04", "a": (  0, 175,  75), "b": ( 55, 175,   0), "c": (50, 200, 100), "star_tint": (100, 200, 130), "pulse_speed": 2.5, "effect": "rain"},
    "lime":        {"bg": "#081400", "a": (155, 255,   0), "b": ( 80, 200,   0), "c": (255, 255, 150), "star_tint": (200, 255, 100), "pulse_speed": 4.0, "effect": "rain"},
    "emerald":     {"bg": "#001408", "a": (  0, 200,  80), "b": (  0, 155,  55), "c": (100, 255, 200), "star_tint": (100, 230, 150), "pulse_speed": 2.8, "effect": "rain"},
    "forest":      {"bg": "#001008", "a": ( 30, 180,  75), "b": (  0, 125,  45), "c": (50, 200, 100), "star_tint": (80, 180, 100), "pulse_speed": 2.2, "effect": "rain"},
    "mint":        {"bg": "#001810", "a": (100, 255, 200), "b": (  0, 210, 160), "c": (220, 255, 245), "star_tint": (150, 255, 220), "pulse_speed": 3.2, "effect": "bubbles"},

    # ── TEAL / CYAN ───────────────────────────────────────────────────
    "teal":        {"bg": "#001414", "a": (  0, 215, 200), "b": (  0, 255, 215), "c": (255, 255, 255), "star_tint": (150, 240, 230), "pulse_speed": 3.0, "effect": "bubbles"},
    "cyan":        {"bg": "#000c14", "a": (  0, 255, 255), "b": (  0, 200, 255), "c": (200, 255, 255), "star_tint": (100, 230, 255), "pulse_speed": 4.0, "effect": "bubbles"},
    "aqua":        {"bg": "#000a10", "a": ( 40, 225, 225), "b": (  0, 185, 205), "c": (150, 255, 255), "star_tint": (100, 210, 220), "pulse_speed": 2.8, "effect": "bubbles"},

    # ── BLUE ──────────────────────────────────────────────────────────
    "blue":        {"bg": "#000814", "a": (  0, 170, 255), "b": (  0, 255, 255), "c": (255, 200, 150), "star_tint": (100, 180, 255), "pulse_speed": 3.0, "effect": "bubbles"},
    "blue dark":   {"bg": "#000408", "a": (  0,  95, 195), "b": (  0, 155, 195), "c": (50, 150, 200), "star_tint": (80, 130, 200), "pulse_speed": 2.5, "effect": "bubbles"},
    "cobalt":      {"bg": "#000814", "a": ( 30, 105, 255), "b": (  0,  60, 205), "c": (100, 200, 255), "star_tint": (80, 120, 255), "pulse_speed": 3.5, "effect": "bubbles"},
    "royal":       {"bg": "#000618", "a": ( 65,  85, 225), "b": (105, 125, 255), "c": (200, 200, 255), "star_tint": (120, 130, 255), "pulse_speed": 2.8, "effect": "warp"},
    "navy":        {"bg": "#000510", "a": ( 40,  60, 180), "b": ( 80, 100, 220), "c": (100, 150, 255), "star_tint": (80, 100, 200), "pulse_speed": 2.2, "effect": "geometry"},

    # ── ICE / FROST ───────────────────────────────────────────────────
    "ice":         {"bg": "#0a0f14", "a": ( 77, 208, 255), "b": (255,  85,  85), "c": (255, 255, 255), "star_tint": (200, 230, 255), "pulse_speed": 2.0, "effect": "snow"},
    "frost":       {"bg": "#0a1018", "a": (160, 220, 255), "b": (205, 240, 255), "c": (255, 255, 255), "star_tint": (220, 240, 255), "pulse_speed": 1.8, "effect": "snow"},
    "arctic":      {"bg": "#080e14", "a": (100, 205, 255), "b": (185, 235, 255), "c": (240, 250, 255), "star_tint": (180, 220, 255), "pulse_speed": 2.2, "effect": "snow"},

    # ── NEON ──────────────────────────────────────────────────────────
    "neon":        {"bg": "#070a10", "a": (  0, 200, 255), "b": (255,  80, 120), "c": (255, 255, 0), "star_tint": (0, 255, 200), "pulse_speed": 5.0, "effect": "warp"},
    "neon green":  {"bg": "#041008", "a": ( 50, 255,  80), "b": (  0, 200, 100), "c": (255, 255, 150), "star_tint": (50, 255, 100), "pulse_speed": 4.5, "effect": "rain"},
    "neon pink":   {"bg": "#100408", "a": (255,  40, 180), "b": (255, 125,  55), "c": (255, 255, 100), "star_tint": (255, 100, 200), "pulse_speed": 5.0, "effect": "paws"},
    "neon purple": {"bg": "#080410", "a": (185,  40, 255), "b": ( 40, 200, 255), "c": (255, 50, 255), "star_tint": (160, 100, 255), "pulse_speed": 4.8, "effect": "warp"},
    "neon orange": {"bg": "#100600", "a": (255, 105,   0), "b": (255, 225,   0), "c": (255, 255, 200), "star_tint": (255, 180, 50), "pulse_speed": 4.2, "effect": "embers"},

    # ── SPECIAL / COSMIC ──────────────────────────────────────────────
    "nebula":      {"bg": "#060010", "a": (130,  60, 255), "b": (255,  60, 150), "c": (255, 200, 255), "star_tint": (180, 150, 255), "pulse_speed": 2.5, "effect": "geometry"},
    "aurora":      {"bg": "#00100c", "a": (  0, 255, 180), "b": (100,  80, 255), "c": (200, 255, 220), "star_tint": (100, 255, 200), "pulse_speed": 3.0, "effect": "warp"},
    "galaxy":      {"bg": "#030610", "a": ( 80, 100, 255), "b": (200,  60, 255), "c": (255, 150, 255), "star_tint": (120, 120, 255), "pulse_speed": 2.8, "effect": "geometry"},
    "plasma":      {"bg": "#080010", "a": (255,  60, 255), "b": ( 80,  60, 255), "c": (255, 200, 255), "star_tint": (200, 100, 255), "pulse_speed": 6.0, "effect": "warp"},
    "inferno":     {"bg": "#100200", "a": (255,  60,   0), "b": (255, 205,  20), "c": (255, 255, 150), "star_tint": (255, 150, 50), "pulse_speed": 4.5, "effect": "embers"},
    "matrix":      {"bg": "#000800", "a": (  0, 255,  60), "b": (  0, 180, 100), "c": (150, 255, 150), "star_tint": (0, 255, 80), "pulse_speed": 3.5, "effect": "rain"},
    "chrome":      {"bg": "#080808", "a": (200, 200, 225), "b": (150, 150, 185), "c": (255, 255, 255), "star_tint": (210, 210, 230), "pulse_speed": 2.0, "effect": "geometry"},

}

# ---------------- STATE ----------------

class State:
    def __init__(self):
        self.port = "auto"          # Default to auto-detect
        self.k1 = "z"
        self.k2 = "x"
        self.theme = "void"

    def load(self):
        if os.path.exists(CONFIG):
            try:
                with open(CONFIG, "r") as f:
                    self.__dict__.update(json.load(f))
            except:
                pass

    def save(self):
        with open(CONFIG, "w") as f:
            json.dump(self.__dict__, f, indent=2)

# ---------------- STAR ----------------

class Star:
    def __init__(self, w, h):
        self.reset(w, h)

    def reset(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.z = random.uniform(0.2, 1.0)

    def update(self, w, h):
        self.x += self.z * 1.4
        self.y += math.sin(self.x * 0.01) * 0.2

        if self.x > w:
            self.reset(0, h)

# ---------------- PARTICLE ENGINE ----------------

class Particle:
    def __init__(self, x, y, effect_type, color):
        self.x, self.y = x, y
        self.type = effect_type
        self.color = color
        self.life = 1.0
        self.decay = random.uniform(0.005, 0.02)
        self.size = random.uniform(4, 12)
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-5, 5)
        self.trail = []
        
        self.char = chr(random.randint(0x30A0, 0x30FF)) if self.type == "rain" else ""

        if self.type == "petals" or self.type == "paws":
            self.vx = random.uniform(-1, 1)
            self.vy = random.uniform(1, 3)
            self.decay = random.uniform(0.002, 0.008)
        elif self.type == "embers":
            self.vx = random.uniform(-0.8, 0.8)
            self.vy = random.uniform(-3, -1)
            self.decay = random.uniform(0.005, 0.015)
        elif self.type == "bubbles":
            self.vx = random.uniform(-0.5, 0.5)
            self.vy = random.uniform(-2, -0.5)
            self.decay = random.uniform(0.002, 0.008)
            self.size = random.uniform(8, 20)
        elif self.type == "rain":
            self.vx = 0
            self.vy = random.uniform(4, 10)
            self.size = random.uniform(8, 20)
            self.decay = random.uniform(0.01, 0.03)
        elif self.type == "snow":
            self.vx = random.uniform(-0.5, 0.5)
            self.vy = random.uniform(0.5, 1.5)
            self.decay = random.uniform(0.002, 0.008)
        elif self.type == "warp":
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(10, 20)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
            self.size = random.uniform(5, 15)
            self.decay = random.uniform(0.02, 0.04)
        else:
            self.vx = random.uniform(-1.5, 1.5)
            self.vy = random.uniform(-1.5, 1.5)

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)
            
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        self.rotation += self.rot_speed
        return self.life > 0

    def draw(self, p):
        alpha = int(255 * self.life)
        if alpha <= 0: return
        
        p.setPen(Qt.PenStyle.NoPen)
        col = QColor(self.color[0], self.color[1], self.color[2], alpha)

        if self.type == "rain":
            p.setFont(QFont("Consolas", 10))
            p.setPen(col)
            p.drawText(QPointF(self.x, self.y), self.char)
            for i, pos in enumerate(self.trail):
                t_alpha = int(alpha * (i / len(self.trail)) * 0.5)
                p.setPen(QColor(self.color[0], self.color[1], self.color[2], t_alpha))
                p.drawText(QPointF(pos[0], pos[1]), self.char)

        elif self.type == "petals":
            p.save()
            p.translate(self.x, self.y)
            p.rotate(self.rotation)
            p.setBrush(col)
            path = QPainterPath()
            path.cubicTo(0, -self.size, self.size, -self.size, 0, 0)
            path.cubicTo(-self.size, -self.size, 0, -self.size, 0, 0)
            p.drawPath(path)
            p.restore()

        elif self.type == "paws":
            p.setBrush(col)
            s = self.size
            p.drawEllipse(QPointF(self.x, self.y + s*0.3), s*0.5, s*0.5)
            p.drawEllipse(QPointF(self.x - s*0.4, self.y - s*0.1), s*0.2, s*0.3)
            p.drawEllipse(QPointF(self.x - s*0.1, self.y - s*0.4), s*0.2, s*0.3)
            p.drawEllipse(QPointF(self.x + s*0.2, self.y - s*0.4), s*0.2, s*0.3)
            p.drawEllipse(QPointF(self.x + s*0.5, self.y - s*0.1), s*0.2, s*0.3)

        elif self.type == "bubbles":
            p.setBrush(QColor(self.color[0], self.color[1], self.color[2], alpha // 5))
            p.setPen(QPen(col, 1))
            p.drawEllipse(QPointF(self.x, self.y), self.size, self.size)
            p.setBrush(QColor(255, 255, 255, alpha // 2))
            p.drawEllipse(QPointF(self.x - self.size*0.3, self.y - self.size*0.3), self.size*0.2, self.size*0.2)

        elif self.type == "embers":
            p.setBrush(col)
            p.drawEllipse(QPointF(self.x, self.y), self.size/3, self.size/3)
            p.setBrush(QColor(self.color[0], self.color[1], self.color[2], alpha // 4))
            p.drawEllipse(QPointF(self.x, self.y), self.size, self.size)

        elif self.type == "snow":
            p.setBrush(col)
            p.drawEllipse(QPointF(self.x, self.y), self.size/2, self.size/2)
            p.setPen(QPen(col, 1))
            p.drawLine(QPointF(self.x - self.size/2, self.y), QPointF(self.x + self.size/2, self.y))
            p.drawLine(QPointF(self.x, self.y - self.size/2), QPointF(self.x, self.y + self.size/2))

        elif self.type == "stars":
            p.save()
            p.translate(self.x, self.y)
            p.rotate(self.rotation)
            p.setBrush(col)
            path = QPainterPath()
            s = self.size
            path.moveTo(0, -s)
            path.lineTo(s*0.2, -s*0.2)
            path.lineTo(s, 0)
            path.lineTo(s*0.2, s*0.2)
            path.lineTo(0, s)
            path.lineTo(-s*0.2, s*0.2)
            path.lineTo(-s, 0)
            path.lineTo(-s*0.2, -s*0.2)
            path.closeSubpath()
            p.drawPath(path)
            p.restore()

        elif self.type == "warp":
            p.setPen(QPen(col, 2))
            if len(self.trail) > 1:
                p.drawLine(QPointF(self.trail[0][0], self.trail[0][1]), QPointF(self.x, self.y))
            else:
                p.drawPoint(QPointF(self.x, self.y))

        else:
            p.save()
            p.translate(self.x, self.y)
            p.rotate(self.rotation)
            p.setBrush(col)
            path = QPainterPath()
            s = self.size
            path.moveTo(0, -s)
            path.lineTo(s*0.6, 0)
            path.lineTo(0, s)
            path.lineTo(-s*0.6, 0)
            path.closeSubpath()
            p.drawPath(path)
            p.restore()

# ---------------- GLOW BUTTON ----------------

class GlowButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._glow = 0.0
        self._press_glow = 0.0
        self._color_a = (255, 255, 255)
        
        self._anim = QPropertyAnimation(self, b"glow_val")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._press_anim = QPropertyAnimation(self, b"press_val")
        self._press_anim.setDuration(150)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(35)

    def set_theme_color(self, col_a):
        self._color_a = col_a

    @pyqtProperty(float)
    def glow_val(self):
        return self._glow

    @glow_val.setter
    def glow_val(self, v):
        self._glow = v
        self.update()

    @pyqtProperty(float)
    def press_val(self):
        return self._press_glow

    @press_val.setter
    def press_val(self, v):
        self._press_glow = v
        self.update()

    def enterEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._press_anim.stop()
        self._press_anim.setStartValue(1.5)
        self._press_anim.setEndValue(0.0)
        self._press_anim.start()
        super().mousePressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 20 + int(self._glow * 40)))
        p.drawRoundedRect(rect, 8, 8)
        
        if self._glow > 0.1 or self._press_glow > 0.1:
            border_alpha = int((self._glow * 120) + (self._press_glow * 120))
            col = QColor(self._color_a[0], self._color_a[1], self._color_a[2], min(255, border_alpha))
            p.setPen(QPen(col, 1.5))
            p.drawRoundedRect(rect, 8, 8)
            
        if self._press_glow > 0.1:
            p.setBrush(QColor(255, 255, 255, int(self._press_glow * 50)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, 8, 8)
        
        text_alpha = 200 + int(self._glow * 55)
        p.setPen(QColor(255, 255, 255, min(255, text_alpha)))
        p.setFont(self.font())
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

# ---------------- CONNECTION INDICATOR ---------------- 

class ConnectionIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._color = QColor(255, 150, 50)  # Default: Orange (searching)
        self._glow = 0.0
        
        # Breathing animation
        self._anim = QPropertyAnimation(self, b"glow_val")
        self._anim.setDuration(1200)
        self._anim.setStartValue(0.2)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)
        self._anim.start()

    @pyqtProperty(float)
    def glow_val(self): 
        return self._glow
    
    @glow_val.setter
    def glow_val(self, v): 
        self._glow = v
        self.update()

    def set_connected(self):
        self._color = QColor(0, 255, 150)  # Green
        
    def set_searching(self):
        self._color = QColor(255, 150, 50) # Orange

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        
        # Outer glow
        alpha = int(60 * self._glow)
        p.setBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), alpha))
        p.drawEllipse(2, 2, 20, 20)
        
        # Core color
        p.setBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), 220))
        p.drawEllipse(5, 5, 14, 14)
        
        # White-hot inner core
        p.setBrush(QColor(255, 255, 255, 150 + int(50 * self._glow)))
        p.drawEllipse(8, 8, 8, 8)

# ---------------- SETTINGS OVERLAY (GX STYLE) ----------------

class SettingsOverlay(QWidget):
    def __init__(self, s, parent=None):
        super().__init__(parent)
        self.s = s
        self.particles = []
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.raise_()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)
        
    def tick(self):
        t = THEMES[self.s.theme]
        effect = t.get("effect", "geometry")
        
        if random.random() < 0.3:
            w, h = self.width(), self.height()
            color = random.choice([t["a"], t["b"], t["c"]])
            if effect in ("rain",):
                p = Particle(random.uniform(0, w), -10, effect, color)
            elif effect in ("petals", "paws", "snow"):
                p = Particle(random.uniform(0, w), -10, effect, color)
            elif effect in ("embers", "bubbles"):
                p = Particle(random.uniform(0, w), h + 10, effect, color)
            else:
                p = Particle(random.uniform(0, w), random.uniform(0, h), effect, color)
                p.decay *= 0.5
            self.particles.append(p)
            
        self.particles = [p for p in self.particles if p.update()]
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        p.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        for particle in self.particles:
            particle.draw(p)

# ---------------- TEST UI ----------------

class Test(QWidget):
    def __init__(self, s):
        super().__init__()

        self.s = s

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.l = 0
        self.r = 0
        self.core = 0
        self.startup_flash = 1.0
        self.radar_angle = 0

        self.stars = [Star(800, 500) for _ in range(140)]
        self.particles = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

        from pynput.keyboard import Listener

        self.listener = Listener(on_press=self.on_key_press)
        self.listener.start()

    def showEvent(self, e):
        self.setFocus()
        self.spawn_theme_effect(150)

    def tick(self):
        w, h = self.width(), self.height()

        for s in self.stars:
            s.update(w, h)

        self.l *= 0.88
        self.r *= 0.88

        t = THEMES[self.s.theme]
        pulse_speed = t.get("pulse_speed", 3.0)
        self.core = 18 + math.sin(time.time() * pulse_speed) * 6
        self.radar_angle += 2

        if self.startup_flash > 0:
            self.startup_flash -= 0.02

        self.particles = [p for p in self.particles if p.update()]

        self.update()

    def spawn_theme_effect(self, count=80):
        t = THEMES[self.s.theme]
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Forced central burst for startup/theme change so it happens once and fades quickly
        for _ in range(count):
            color = random.choice([t["a"], t["b"], t["c"]])
            p = Particle(cx, cy, "geometry", color)
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 6)
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.decay = random.uniform(0.01, 0.025) # Fast decay so it doesn't linger like rain
            self.particles.append(p)

    def spawn_key_effect(self, x, y, color_list):
        # Always a sharp, fast burst for key presses
        for _ in range(25):
            color = random.choice(color_list)
            p = Particle(x, y, "geometry", color)
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 8)
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.decay = random.uniform(0.025, 0.05) # Disappears quickly
            p.size *= 0.7
            self.particles.append(p)

    def glow_ring(self, p, x, y, r, col, intensity=1.0):
        for i in range(8):
            p.setPen(Qt.PenStyle.NoPen)
            alpha = max(0, int((50 - i * 6) * intensity))
            p.setBrush(QColor(col[0], col[1], col[2], alpha))
            p.drawEllipse(QPointF(x, y), r + i * 6, r + i * 6)

        p.setBrush(QColor(*col, 240))
        p.drawEllipse(QPointF(x, y), r, r)

        p.setBrush(QColor(255, 255, 255, 120))
        p.drawEllipse(QPointF(x, y), r * 0.4, r * 0.4)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = THEMES[self.s.theme]
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        p.fillRect(self.rect(), QColor(t["bg"]))

        r_a, g_a, b_a = t["a"]
        r_b, g_b, b_b = t["b"]
        
        grad = QRadialGradient(cx, cy, 300)
        grad.setColorAt(0.0, QColor(r_a, g_a, b_a, 25))
        grad.setColorAt(0.5, QColor(r_b, g_b, b_b, 10))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())

        star_tint = t.get("star_tint", (255, 255, 255))
        for s in self.stars:
            p.setPen(Qt.PenStyle.NoPen)
            alpha = int(180 * s.z)
            p.setBrush(QColor(star_tint[0], star_tint[1], star_tint[2], alpha))
            p.drawEllipse(QPointF(s.x, s.y), 2.0 * s.z, 2.0 * s.z)

        p.setPen(QPen(QColor(star_tint[0], star_tint[1], star_tint[2], 20), 1))
        for i in range(len(self.stars)):
            for j in range(i+1, len(self.stars)):
                s1, s2 = self.stars[i], self.stars[j]
                dist = math.hypot(s1.x - s2.x, s1.y - s2.y)
                if dist < 60:
                    p.drawLine(QPointF(s1.x, s1.y), QPointF(s2.x, s2.y))

        breathe = math.sin(time.time() * 1.5) * 3

        for particle in self.particles:
            particle.draw(p)

        self.glow_ring(p, cx - 140, cy + breathe, self.l, t["a"])
        self.glow_ring(p, cx + 140, cy - breathe, self.r, t["b"])

        core_color = t.get("c", (0, 255, 200))
        self.glow_ring(p, cx, cy, self.core, core_color, intensity=1.5)
        
        p.setPen(QPen(QColor(core_color[0], core_color[1], core_color[2], 50), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(cx, cy)
        p.rotate(time.time() * 30)
        p.drawEllipse(QPointF(0, 0), 30, 30)
        p.drawEllipse(QPointF(0, 0), 35, 35)
        for i in range(12):
            p.drawLine(QPointF(30, 0), QPointF(35, 0))
            p.rotate(30)
        p.restore()

        radar_alpha = int(50 * (1.0 - (self.radar_angle % 100) / 100.0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(core_color[0], core_color[1], core_color[2], radar_alpha))
        p.drawEllipse(QPointF(cx, cy), self.radar_angle % 100, self.radar_angle % 100)

        if self.startup_flash > 0:
            flash_alpha = int(255 * self.startup_flash)
            p.fillRect(self.rect(), QColor(255, 255, 255, flash_alpha))

    def on_key_press(self, key):
        try:
            k = key.char.lower() if hasattr(key, 'char') and key.char else None
        except:
            k = None

        special_map = {
            Key.up: "up", Key.down: "down", Key.left: "left", Key.right: "right",
            Key.space: "space", Key.enter: "enter", Key.tab: "tab",
            Key.shift: "shift", Key.ctrl: "ctrl", Key.alt: "alt",
            Key.backspace: "backspace", Key.esc: "esc"
        }

        if key in special_map:
            k = special_map[key]

        t = THEMES[self.s.theme]
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        if k == self.s.k1:
            self.l = 20
            self.spawn_key_effect(cx - 140, cy, [t["a"], t["c"]])

        if k == self.s.k2:
            self.r = 20
            self.spawn_key_effect(cx + 140, cy, [t["b"], t["c"]])

# ---------------- ENGINE ----------------                                   

class Engine(threading.Thread):
    def __init__(self, s, test):
        super().__init__(daemon=True)

        self.s = s
        self.test = test

        self.ser = None
        self.running = True
        self.force_reconnect = False       # Flag to force reconnection

        self.prev = [0, 0]

        self.special_map = {
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "space": Key.space, "enter": Key.enter, "tab": Key.tab,
            "shift": Key.shift, "ctrl": Key.ctrl, "alt": Key.alt,
            "backspace": Key.backspace, "esc": Key.esc
        }

        self.connected_port = None         # Track which port we actually connected to

    def get_key(self, key_str):
        return self.special_map.get(key_str, key_str)

    def _scan_ports(self):
        """Return a prioritised list of (device, description, is_arduino) tuples."""
        return scan_serial_ports()

    def _try_open(self, port_name):
        """Try to open a serial port. Returns the Serial object or None."""
        try:
            ser = serial.Serial(port_name, 115200, timeout=1)
            time.sleep(2)                  # Wait for Arduino reset
            return ser
        except Exception:
            return None

    def _verify_arduino(self, ser, timeout=5):
        """Try to read a valid 'a,b' line within *timeout* seconds."""
        deadline = time.time() + timeout
        while time.time() < deadline and self.running:
            try:
                line = ser.readline().decode(errors="ignore").strip()
                if line and "," in line:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        int(parts[0]); int(parts[1])
                        return True
            except Exception:
                pass
        return False

    def connect(self):
        """Auto-detect and connect to an Arduino.  Tries the configured port
        first (if set), then falls back to scanning every available port."""
        while self.running:
            # ── 1. Try the user-configured port first ──────────────
            configured = self.s.port
            if configured and configured not in ("auto", ""):
                ser = self._try_open(configured)
                if ser:
                    if self._verify_arduino(ser, timeout=4):
                        self.ser = ser
                        self.connected_port = configured
                        return
                    ser.close()

            # ── 2. Auto-scan all ports ─────────────────────────────
            ports = self._scan_ports()
            for port_name, desc, is_arduino in ports:
                if not self.running:
                    return
                ser = self._try_open(port_name)
                if ser:
                    if self._verify_arduino(ser, timeout=4):
                        self.ser = ser
                        self.connected_port = port_name
                        self.s.port = port_name
                        self.s.save()
                        return
                    # Port opened but no valid data – still accept it
                    self.ser = ser
                    self.connected_port = port_name
                    self.s.port = port_name
                    self.s.save()
                    return

            # ── 3. Nothing found – wait and retry ──────────────────
            time.sleep(3)

    def run(self):
        self.connect()

        while self.running:
            # Handle forced reconnection
            if self.force_reconnect:
                self.force_reconnect = False
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                self.connected_port = None
                self.connect()

            try:
                if not self.ser or not self.ser.is_open:
                    self.connect()

                line = self.ser.readline().decode(errors="ignore").strip()

                if not line or "," not in line:
                    continue

                a, b = map(int, line.split(","))
                k1_obj = self.get_key(self.s.k1)

                if a == 1 and self.prev[0] == 0:
                    self.test.l = 20
                    kb.press(k1_obj)
                elif a == 0 and self.prev[0] == 1:
                    kb.release(k1_obj)

                k2_obj = self.get_key(self.s.k2)

                if b == 1 and self.prev[1] == 0:
                    self.test.r = 20
                    kb.press(k2_obj)
                elif b == 0 and self.prev[1] == 1:
                    kb.release(k2_obj)

                self.prev = [a, b]

            except Exception:
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                self.connected_port = None
                self.connect()

# ---------------- THEME PANEL ----------------

class ThemePanel(QWidget):
    TILE_W = 104; TILE_H = 72; TILE_GAP = 6
    PAD_X = 10; PAD_Y = 10; PANEL_H = TILE_H + PAD_Y * 2
    SCROLL_STEP = 120

    def __init__(self, parent, s, theme_btn, on_theme_select):
        super().__init__(parent)
        self.s = s; self.theme_btn = theme_btn; self.on_theme_select = on_theme_select
        self._is_open = False; self._scroll_x = 0; self._hovered_idx = -1
        self.theme_names = list(THEMES.keys())

        self._content_w = (len(self.theme_names) * self.TILE_W + (len(self.theme_names) - 1) * self.TILE_GAP + self.PAD_X * 2)

        bx, by = self._btn_xy()
        self.setGeometry(bx, by, parent.width() - bx, 0)
        self.setVisible(False); self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(240); self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._scroll_anim = QPropertyAnimation(self, b"scroll_x")
        self._scroll_anim.setDuration(200); self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.raise_()

    @pyqtProperty(float)
    def scroll_x(self): return self._scroll_x
    @scroll_x.setter
    def scroll_x(self, val): self._scroll_x = val; self.update()

    def _btn_xy(self):
        pos = self.theme_btn.mapTo(self.parent(), QPoint(0, self.theme_btn.height()))
        return pos.x(), pos.y()

    def _open_rect(self):
        bx, by = self._btn_xy(); return QRect(bx, by, self.parent().width() - bx, self.PANEL_H)

    def _closed_rect(self):
        bx, by = self._btn_xy(); return QRect(bx, by, self.parent().width() - bx, 0)

    def _tile_rect(self, idx):
        x = self.PAD_X + idx * (self.TILE_W + self.TILE_GAP) - self._scroll_x; y = self.PAD_Y
        return QRectF(x, y, self.TILE_W, self.TILE_H)

    def _idx_at(self, mouse_x):
        for i in range(len(self.theme_names)):
            r = self._tile_rect(i)
            if r.left() <= mouse_x <= r.right(): return i
        return -1

    def _clamp_scroll(self, target):
        max_scroll = max(0, self._content_w - self.width()); return max(0, min(target, max_scroll))

    def open_panel(self):
        if self._is_open: return
        self._is_open = True; self.setVisible(True); self.raise_()
        try: self._anim.finished.disconnect()
        except: pass
        self._anim.stop(); self._anim.setStartValue(self._closed_rect()); self._anim.setEndValue(self._open_rect()); self._anim.start()

    def close_panel(self):
        if not self._is_open: return
        self._is_open = False
        try: self._anim.finished.disconnect()
        except: pass
        self._anim.stop(); self._anim.setStartValue(self._open_rect()); self._anim.setEndValue(self._closed_rect())
        self._anim.finished.connect(lambda: self.setVisible(False)); self._anim.start()

    def toggle(self):
        if self._is_open: self.close_panel()
        else: self.open_panel()

    def mouseMoveEvent(self, e):
        new_idx = self._idx_at(e.position().x())
        if new_idx != self._hovered_idx: self._hovered_idx = new_idx; self.update()

    def leaveEvent(self, e): self._hovered_idx = -1; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            idx = self._idx_at(e.position().x())
            if idx >= 0: self.on_theme_select(self.theme_names[idx]); self.update(); self.close_panel()

    def wheelEvent(self, e):
        delta = -int(e.angleDelta().y() / 8); step = self.SCROLL_STEP * (1 if delta > 0 else -1)
        target = self._clamp_scroll(self._scroll_x + step)
        self._scroll_anim.stop(); self._scroll_anim.setStartValue(self._scroll_x); self._scroll_anim.setEndValue(target); self._scroll_anim.start()

    def paintEvent(self, e):
        if self.height() < 4: return
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(12, 4, 24, 180)); p.drawRoundedRect(0, 0, w, h, 10, 10)
        sheen = QLinearGradient(0, 0, 0, h * 0.55)
        sheen.setColorAt(0.0, QColor(255, 255, 255, 28)); sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(sheen); p.drawRoundedRect(0, 0, w, h, 10, 10)
        p.setPen(QPen(QColor(255, 255, 255, 45), 1)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawRoundedRect(0, 0, w, h, 10, 10)

        t = THEMES[self.s.theme]; r_a, g_a, b_a = t["a"]
        p.setPen(QPen(QColor(r_a, g_a, b_a, 180), 2)); p.drawLine(14, 1, w - 14, 1)

        clip = QPainterPath(); clip.addRoundedRect(QRectF(0, 0, w, h), 10, 10); p.setClipPath(clip)
        for idx, name in enumerate(self.theme_names): self._draw_tile(p, idx, name)

    def _draw_tile(self, p, idx, name):
        r = self._tile_rect(idx); theme = THEMES[name]
        r_a, g_a, b_a = theme["a"]; r_b, g_b, b_b = theme["b"]
        active = (name == self.s.theme); hovered = (idx == self._hovered_idx)
        if r.right() < 0 or r.left() > self.width(): return

        bg_alpha = 190 if active else 120 if hovered else 55
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(r_a, g_a, b_a, bg_alpha // 4)); p.drawRoundedRect(r, 8, 8)

        bar_h = 5; bar_rect = QRectF(r.x(), r.y(), r.width(), bar_h)
        grad = QLinearGradient(r.x(), 0, r.x() + r.width(), 0)
        grad.setColorAt(0.0, QColor(r_a, g_a, b_a, 255)); grad.setColorAt(1.0, QColor(r_b, g_b, b_b, 255))
        p.setBrush(grad); p.drawRoundedRect(bar_rect, 3, 3)

        dot_r = 6; dot_cx = r.x() + r.width() / 2 - dot_r - 3; dot_cy = r.y() + bar_h + 10
        p.setBrush(QColor(r_a, g_a, b_a, 55)); p.drawEllipse(QPointF(dot_cx, dot_cy + dot_r), dot_r + 4, dot_r + 4)
        p.setBrush(QColor(r_a, g_a, b_a, 230)); p.drawEllipse(QPointF(dot_cx, dot_cy + dot_r), dot_r, dot_r)
        dot_cx_b = dot_cx + dot_r * 2 + 6
        p.setBrush(QColor(r_b, g_b, b_b, 55)); p.drawEllipse(QPointF(dot_cx_b, dot_cy + dot_r), dot_r + 4, dot_r + 4)
        p.setBrush(QColor(r_b, g_b, b_b, 230)); p.drawEllipse(QPointF(dot_cx_b, dot_cy + dot_r), dot_r, dot_r)

        font = QFont(); font.setPointSize(8); font.setBold(active); font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8); p.setFont(font)
        label_alpha = 255 if (active or hovered) else 160; p.setPen(QColor(255, 255, 255, label_alpha))
        p.drawText(QRectF(r.x(), r.y() + bar_h + dot_r * 2 + 16, r.width(), 18), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, name.upper())

        if active: p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(r_a, g_a, b_a, 220), 1.5)); p.drawRoundedRect(r, 8, 8)
        elif hovered: p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(255, 255, 255, 60), 1)); p.drawRoundedRect(r, 8, 8)

# ---------------- SETTINGS ----------------

class Settings(QWidget):
    def __init__(self, s, apply_theme, engine_ref=None):
        super().__init__()

        self.s = s
        self.apply_theme = apply_theme
        self.engine_ref = engine_ref

        self.setFixedSize(700, 400)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.bind_k1 = False
        self.bind_k2 = False

        self.k1_btn = GlowButton(f"K1: {s.k1}")
        self.k2_btn = GlowButton(f"K2: {s.k2}")

        self.theme_btn = GlowButton("THEME")
        self.video_btn = GlowButton("RANDOM VIDEO")
        self.save_btn = GlowButton("SAVE")

        # ── Port selector widgets ──────────────────────────
        self.port_label = QLabel("SERIAL PORT")
        self.port_label.setStyleSheet("color: rgba(255,255,255,140); font-size: 10px; font-weight: bold; letter-spacing: 2px;")

        self.port_combo = QComboBox()
        self.port_combo.setMinimumHeight(38)
        self.port_combo.addItem("Auto Detect", "auto")

        self.refresh_btn = GlowButton("↻")
        self.refresh_btn.setFixedSize(42, 38)
        self.refresh_btn.setToolTip("Refresh port list")

        self.port_indicator = ConnectionIndicator()

        self.port_status_text = QLabel("Initializing...")
        self.port_status_text.setStyleSheet("color: rgba(255,255,255,100); font-size: 10px;")

        self._refresh_port_list()

        self.port_combo.currentIndexChanged.connect(self._on_port_changed)
        self.refresh_btn.clicked.connect(self._refresh_port_list)
        # ── End port selector ──────────────────────────────

        self.k1_btn.clicked.connect(self.bind_k1_start)
        self.k2_btn.clicked.connect(self.bind_k2_start)

        self.theme_btn.clicked.connect(self.toggle_theme_panel)
        self.video_btn.clicked.connect(self.load_random_video)
        self.save_btn.clicked.connect(self.save)

        # Layout setup
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(self.k1_btn)
        layout.addWidget(self.k2_btn)

        # ── Port row layout ────────────────────────────────
        port_container = QVBoxLayout()
        port_container.setSpacing(4)
        
        port_header = QHBoxLayout()
        port_header.addWidget(self.port_label)
        port_header.addStretch()
        port_header.addWidget(self.port_status_text)
        port_container.addLayout(port_header)

        port_row = QHBoxLayout()
        port_row.setSpacing(8)
        port_row.addWidget(self.port_indicator)
        port_row.addWidget(self.port_combo, stretch=1)
        port_row.addWidget(self.refresh_btn)
        port_container.addLayout(port_row)
        
        layout.addLayout(port_container)
        layout.addSpacing(10)
        # ── End port row ───────────────────────────────────

        row = QHBoxLayout()
        row.addWidget(self.theme_btn)
        row.addWidget(self.video_btn)
        row.addWidget(self.save_btn)
        layout.addLayout(row)
        layout.addStretch()

        # Video setup
        self.cap = None
        self.frame = None
        self._auto_load_video()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video)
        self.timer.start(30)

        # ── Status update timer ────────────────────────────
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_port_status)
        self.status_timer.start(1000)
        # ── End status timer ───────────────────────────────

        # GX Style Overlay setup
        self.overlay = SettingsOverlay(self.s, self)
        self.overlay.setGeometry(0, 0, 700, 400)
        self.overlay.lower()

        self.theme_panel = None
        QTimer.singleShot(0, self._init_theme_panel)

    def _init_theme_panel(self):
        self.theme_panel = ThemePanel(self, self.s, self.theme_btn, self._on_theme_selected)

    def _on_theme_selected(self, name):
        self.s.theme = name; self.s.save(); self.apply_theme()
        if self.theme_panel: self.theme_panel.update()

    def toggle_theme_panel(self):
        if self.theme_panel: self.theme_panel.toggle()

    def bind_k1_start(self):
        self.bind_k1 = True; self.bind_k2 = False
        self.k1_btn.setText("Press any key/arrow..."); self.setFocus()

    def bind_k2_start(self):
        self.bind_k2 = True; self.bind_k1 = False
        self.k2_btn.setText("Press any key/arrow..."); self.setFocus()

    def keyPressEvent(self, e):
        key_map = {
            Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right",
            Qt.Key.Key_Space: "space", Qt.Key.Key_Enter: "enter", Qt.Key.Key_Return: "enter", Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Shift: "shift", Qt.Key.Key_Control: "ctrl", Qt.Key.Key_Alt: "alt",
            Qt.Key.Key_Backspace: "backspace", Qt.Key.Key_Escape: "esc"
        }
        key_val = key_map.get(e.key(), e.text().lower())
        if not key_val: return

        if self.bind_k1: self.s.k1 = key_val; self.k1_btn.setText(f"K1: {key_val}"); self.bind_k1 = False
        elif self.bind_k2: self.s.k2 = key_val; self.k2_btn.setText(f"K2: {key_val}"); self.bind_k2 = False
        self.s.save()

    # ── Port management methods ────────────────────────────
    def _refresh_port_list(self):
        current = self.s.port
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        self.port_combo.addItem("⟐ AUTO DETECT", "auto")

        ports = scan_serial_ports()
        for dev, desc, is_arduino in ports:
            label = f"{dev}  {'⮕ ' if is_arduino else ''}{desc}"
            self.port_combo.addItem(label, dev)

        idx = self.port_combo.findData(current)
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)
        else:
            self.port_combo.setCurrentIndex(0)

        self.port_combo.blockSignals(False)
        self._update_port_status()

    def _on_port_changed(self, index):
        data = self.port_combo.itemData(index)
        if data is None: return
        self.s.port = data
        self.s.save()

        if self.engine_ref:
            self.engine_ref.force_reconnect = True

        self._update_port_status()

    def _update_port_status(self):
        if self.engine_ref and self.engine_ref.connected_port:
            port = self.engine_ref.connected_port
            self.port_status_text.setText(f"SYNCED: {port}")
            self.port_status_text.setStyleSheet("color: rgba(0,255,150,180); font-size: 10px; font-weight: bold;")
            self.port_indicator.set_connected()
        elif self.engine_ref and self.engine_ref.ser and self.engine_ref.ser.is_open:
            port = self.engine_ref.ser.port
            self.port_status_text.setText(f"SYNCED: {port}")
            self.port_status_text.setStyleSheet("color: rgba(0,255,150,180); font-size: 10px; font-weight: bold;")
            self.port_indicator.set_connected()
        else:
            self.port_status_text.setText("SCANNING...")
            self.port_status_text.setStyleSheet("color: rgba(255,150,50,180); font-size: 10px; font-weight: bold;")
            self.port_indicator.set_searching()
    # ── End port management ────────────────────────────────

    def _auto_load_video(self):
        vids = []
        for ext in ("*.mp4", "*.webm", "*.avi", "*.mkv", "*.mov"):
            vids += glob.glob(os.path.join(VIDEO_FOLDER, ext))
        if vids:
            if self.cap: self.cap.release()
            self.cap = cv2.VideoCapture(random.choice(vids))

    def load_random_video(self):
        vids = []
        for ext in ("*.mp4", "*.webm", "*.avi", "*.mkv", "*.mov"):
            vids += glob.glob(os.path.join(VIDEO_FOLDER, ext))
        if not vids: return
        choice = random.choice(vids)
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(choice)

    def update_video(self):
        if not self.cap: return
        ret, frame = self.cap.read()
        if not ret: self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0); return
        frame = cv2.resize(frame, (700, 400))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.frame = QPixmap.fromImage(img)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        if self.frame: p.drawPixmap(0, 0, self.frame)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'overlay'): self.overlay.setGeometry(0, 0, self.width(), self.height())

    def save(self): self.s.save()

# ---------------- MAIN APP ───────────────────────────────────────────────── 

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.s = State(); self.s.load()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(700, 400)

        self.stack = QStackedWidget()
        self.test = Test(self.s)
        self.engine = Engine(self.s, self.test); self.engine.start()

        self.settings = Settings(self.s, self.apply_theme, engine_ref=self.engine)

        self.stack.addWidget(self.test)
        self.stack.addWidget(self.settings)

        self.b1 = GlowButton("TEST")
        self.b2 = GlowButton("SETTINGS")
        self.exit_btn = GlowButton("EXIT")

        self.b1.clicked.connect(lambda: (self.stack.setCurrentIndex(0), self.test.setFocus()))
        self.b2.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.exit_btn.clicked.connect(QApplication.quit)

        top = QHBoxLayout()
        top.addWidget(self.b1); top.addWidget(self.b2); top.addWidget(self.exit_btn)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.stack)

        self.apply_theme()

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon.fromTheme("applications-system")); self.tray.setVisible(True)
        menu = QMenu()
        show_action = QAction("Show"); exit_action = QAction("Exit")
        show_action.triggered.connect(self.show_window); exit_action.triggered.connect(QApplication.quit)
        menu.addAction(show_action); menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_click)
        QApplication.instance().focusChanged.connect(self.on_focus_changed)

    def apply_theme(self):
        t = THEMES[self.s.theme]
        self.setStyleSheet(f"""
            QWidget {{ background: {t['bg']}; color: white; }}
            QListWidget {{ background: rgba(0,0,0,0.4); border: none; padding: 6px; }}
            QListWidget::item {{ padding: 8px; }}
            QListWidget::item:selected {{ background: rgba(255,255,255,0.2); }}
            
            QComboBox {{
                background: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 6px;
                padding: 6px 12px;
                color: rgba(255,255,255,220);
                font-family: Consolas;
                font-size: 12px;
                letter-spacing: 1px;
            }}
            QComboBox:hover {{
                background: rgba(255, 255, 255, 25);
                border: 1px solid rgba({t['a'][0]}, {t['a'][1]}, {t['a'][2]}, 150);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid rgba({t['a'][0]}, {t['a'][1]}, {t['a'][2]}, 200);
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background: rgba(15, 5, 30, 240);
                border: 1px solid rgba({t['a'][0]}, {t['a'][1]}, {t['a'][2]}, 100);
                border-radius: 6px;
                padding: 6px;
                color: white;
                outline: none;
                font-family: Consolas;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                min-height: 26px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: rgba({t['a'][0]}, {t['a'][1]}, {t['a'][2]}, 50);
            }}
            QComboBox QAbstractItemView::item:selected {{
                background: rgba({t['a'][0]}, {t['a'][1]}, {t['a'][2]}, 80);
                border-left: 2px solid rgba({t['a'][0]}, {t['a'][1]}, {t['a'][2]}, 255);
            }}
        """)

        for btn in [self.b1, self.b2, self.exit_btn, self.settings.k1_btn, self.settings.k2_btn,
                    self.settings.theme_btn, self.settings.video_btn, self.settings.save_btn,
                    self.settings.refresh_btn]:
            btn.set_theme_color(t["a"])

        self.test.spawn_theme_effect(100)

    def on_focus_changed(self, old, new):
        if not self.isVisible(): return
        active = QApplication.activeWindow()
        if active is None or not self.isAncestorOf(active):
            self.hide()
            self.tray.showMessage("Holo System", "Running in background", QSystemTrayIcon.MessageIcon.NoIcon, 1000)

    def tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger: self.show_window()

    def show_window(self):
        self.show(); self.raise_(); self.activateWindow()

# ---------------- START ----------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec())