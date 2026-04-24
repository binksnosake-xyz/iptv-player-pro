
import sys
import os
import json
import requests
import threading
import time
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False

APP_NAME = "IPTV Ultra"
DEVELOPER = "Développé par Idir BINKSNOSAKE"
DATA_FILE = os.path.join(os.path.expanduser("~"), ".iptv_ultra_data.json")

# ─── PERSISTENCE ─────────────────────────────────────────────────────────────
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {"playlists": [], "favorites": [], "resume": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

# ─── STYLES ──────────────────────────────────────────────────────────────────
STYLE = """
QMainWindow, QWidget, QDialog {
    background-color: #0d0d0d;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QLabel { color: #ffffff; background: transparent; }
QLineEdit {
    background-color: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 9px 14px;
    color: #ffffff;
    font-size: 13px;
}
QLineEdit:focus { border: 1px solid #e50914; }
QPushButton {
    background-color: #e50914;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 22px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover { background-color: #ff2020; }
QPushButton:pressed { background-color: #b0070f; }
QPushButton#flat {
    background: transparent;
    color: #aaa;
    border: 1px solid #2a2a2a;
    padding: 8px 16px;
    font-weight: normal;
}
QPushButton#flat:hover { background: #1e1e1e; color: #fff; border-color: #e50914; }
QPushButton#icon_btn {
    background: transparent;
    border: none;
    padding: 4px;
    font-size: 18px;
    color: #aaa;
}
QPushButton#icon_btn:hover { color: #e50914; }
QListWidget {
    background-color: #111;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 11px 14px;
    border-bottom: 1px solid #1a1a1a;
    color: #ccc;
    font-size: 13px;
}
QListWidget::item:selected { background: #e50914; color: #fff; }
QListWidget::item:hover { background: #1e1e1e; color: #fff; }
QScrollBar:vertical { background: #111; width: 5px; border-radius: 3px; }
QScrollBar::handle:vertical { background: #333; border-radius: 3px; }
QScrollBar::handle:vertical:hover { background: #e50914; }
QScrollBar:horizontal { background: #111; height: 5px; }
QScrollBar::handle:horizontal { background: #333; border-radius: 3px; }
QComboBox {
    background: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 6px 12px;
    color: #fff;
    font-size: 12px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: #1e1e1e; border: 1px solid #333; color: #fff; }
QSlider::groove:horizontal {
    background: #333;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #e50914;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal { background: #e50914; border-radius: 2px; }
QProgressBar {
    background: #1e1e1e;
    border-radius: 3px;
    height: 4px;
    text-align: center;
    font-size: 0px;
}
QProgressBar::chunk { background: #e50914; border-radius: 3px; }
QTabWidget::pane { border: none; background: #0d0d0d; }
QTabBar::tab {
    background: transparent;
    color: #666;
    padding: 10px 20px;
    font-size: 13px;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: #e50914; border-bottom: 2px solid #e50914; }
QTabBar::tab:hover { color: #fff; }
QMenu {
    background: #1a1a1a;
    border: 1px solid #333;
    color: #fff;
    padding: 4px;
}
QMenu::item { padding: 8px 20px; border-radius: 4px; }
QMenu::item:selected { background: #e50914; }
QToolTip { background: #1a1a1a; color: #fff; border: 1px solid #333; padding: 4px 8px; }
"""

NAV_STYLE = """
QPushButton {
    background: transparent;
    color: #777;
    border: none;
    border-radius: 8px;
    padding: 11px 18px;
    font-size: 13px;
    text-align: left;
}
QPushButton:hover { background: #1a1a1a; color: #fff; }
QPushButton[active="true"] {
    background: #1a1a1a;
    color: #e50914;
    font-weight: bold;
    border-left: 3px solid #e50914;
}
"""

# ─── XTREAM API ───────────────────────────────────────────────────────────────
class XtreamAPI:
    def __init__(self, server, username, password):
        self.server = self._normalize_server(server)
        self.username = self._safe_text(username)
        self.password = self._safe_text(password)
        self.base = self.server + "/player_api.php?username=" + self.username + "&password=" + self.password

    def _safe_text(self, x):
        # Force pure string digit-by-digit to avoid scientific notation
        raw = x if isinstance(x, str) else repr(x)
        # Rebuild char by char to guarantee no float conversion
        result = ""
        for c in raw:
            result += c
        return result.strip()

    def _normalize_server(self, s):
        s = (s if isinstance(s, str) else str(s)).strip().rstrip("/")
        if not s.startswith("http://") and not s.startswith("https://"):
            s = "http://" + s
        return s

    def _get(self, url, timeout=20):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except:
            return None

    def get_info(self):
        return self._get(self.base, timeout=15)

    def get_live_categories(self):   return self._get(f"{self.base}&action=get_live_categories") or []
    def get_live_streams(self, cid=None):
        url = f"{self.base}&action=get_live_streams"
        if cid: url += f"&category_id={cid}"
        return self._get(url) or []
    def get_vod_categories(self):    return self._get(f"{self.base}&action=get_vod_categories") or []
    def get_vod_streams(self, cid=None):
        url = f"{self.base}&action=get_vod_streams"
        if cid: url += f"&category_id={cid}"
        return self._get(url) or []
    def get_series_categories(self): return self._get(f"{self.base}&action=get_series_categories") or []
    def get_series(self, cid=None):
        url = f"{self.base}&action=get_series"
        if cid: url += f"&category_id={cid}"
        return self._get(url) or []
    def get_series_info(self, sid):  return self._get(f"{self.base}&action=get_series_info&series_id={sid}") or {}

    def live_url(self, sid):   return f"{self.server}/live/{self.username}/{self.password}/{sid}.ts"
    def vod_url(self, sid, ext="mp4"):    return f"{self.server}/movie/{self.username}/{self.password}/{sid}.{ext}"
    def episode_url(self, sid, ext="mp4"): return f"{self.server}/series/{self.username}/{self.password}/{sid}.{ext}"

# ─── WORKERS ─────────────────────────────────────────────────────────────────
class LoginWorker(QThread):
    ok = pyqtSignal(object, dict)
    fail = pyqtSignal()
    def __init__(self, servers, u, p):
        super().__init__()
        self.servers = servers; self.u = u; self.p = p
    def run(self):
        for s in self.servers:
            api = XtreamAPI(s, str(self.u).strip(), str(self.p).strip())
            info = api.get_info()
            print("BASE=", api.base)
print("INFO=", info)
            if info and "user_info" in info:
                self.ok.emit(api, info)
                return
        self.fail.emit()
# ─── APP ICON ─────────────────────────────────────────────────────────────────
def make_icon(size=64):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(229, 9, 20))
    p.setPen(Qt.NoPen)
    p.drawEllipse(0, 0, size, size)
    p.setBrush(QColor(255, 255, 255))
    m = size // 4
    tri = QPolygon([QPoint(m+2, m), QPoint(m+2, size-m), QPoint(size-m+2, size//2)])
    p.drawPolygon(tri)
    p.end()
    return QIcon(pix)

# ─── CLOCK WIDGET ────────────────────────────────────────────────────────────
class ClockLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("color: #aaa; font-size: 13px; font-weight: bold; background: transparent;")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        self._tick()
    def _tick(self):
        self.setText(datetime.now().strftime("%H:%M"))

# ─── VIDEO PLAYER ─────────────────────────────────────────────────────────────
class VideoPlayer(QWidget):
    def __init__(self, app_data, save_fn):
        super().__init__()
        self.app_data = app_data
        self.save_fn = save_fn
        self.current_url = None
        self.current_key = None
        self.current_name = None
        self.is_live = False
        self._fullscreen = False
        self._controls_hidden = False
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._auto_hide_controls)
        self._resume_timer = QTimer(self)
        self._resume_timer.setInterval(5000)
        self._resume_timer.timeout.connect(self._save_position)
        self.setMouseTracking(True)
        self._build_ui()
        if VLC_AVAILABLE:
            self.instance = vlc.Instance(
                "--no-xlib", "--network-caching=2000", "--live-caching=2000",
                "--file-caching=2000", "--disc-caching=2000",
                "--ts-trust-pcr", "--demux=ts,mp4,mkv",
                "--avcodec-hw=any"
            )
            self.mp = self.instance.media_player_new()
            em = self.mp.event_manager()
            em.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end)
        else:
            self.instance = None
            self.mp = None

    def _build_ui(self):
        self.setStyleSheet("background:#000;")
        self.setMinimumHeight(280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        # Video surface
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background:#000;")
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_frame.setMouseTracking(True)
        layout.addWidget(self.video_frame)

        # Controls overlay
        self.controls = QFrame()
        self.controls.setFixedHeight(90)
        self.controls.setStyleSheet("QFrame{background:qlineargradient(y1:0,y2:1,stop:0 rgba(0,0,0,0),stop:1 rgba(0,0,0,200));}")
        cl = QVBoxLayout(self.controls)
        cl.setContentsMargins(12, 4, 12, 8)
        cl.setSpacing(4)

        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self._seek)
        self.progress_slider.hide()
        cl.addWidget(self.progress_slider)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.play_btn = QPushButton("⏸")
        self.play_btn.setObjectName("icon_btn")
        self.play_btn.setFixedSize(36,36)
        self.play_btn.clicked.connect(self.toggle_pause)
        btn_row.addWidget(self.play_btn)

        self.back_btn = QPushButton("⏪ 10s")
        self.back_btn.setObjectName("icon_btn")
        self.back_btn.setFixedHeight(30)
        self.back_btn.clicked.connect(lambda: self._skip(-10))
        self.back_btn.hide()
        btn_row.addWidget(self.back_btn)

        self.fwd_btn = QPushButton("10s ⏩")
        self.fwd_btn.setObjectName("icon_btn")
        self.fwd_btn.setFixedHeight(30)
        self.fwd_btn.clicked.connect(lambda: self._skip(10))
        self.fwd_btn.hide()
        btn_row.addWidget(self.fwd_btn)

        self.time_lbl = QLabel("00:00 / 00:00")
        self.time_lbl.setStyleSheet("color:#ccc;font-size:11px;background:transparent;")
        btn_row.addWidget(self.time_lbl)

        btn_row.addStretch()

        self.now_lbl = QLabel("")
        self.now_lbl.setStyleSheet("color:#eee;font-size:12px;font-weight:bold;background:transparent;")
        btn_row.addWidget(self.now_lbl)

        btn_row.addStretch()

        # Audio tracks
        self.audio_combo = QComboBox()
        self.audio_combo.setFixedWidth(120)
        self.audio_combo.setToolTip("Piste audio")
        self.audio_combo.currentIndexChanged.connect(self._set_audio)
        self.audio_combo.hide()
        btn_row.addWidget(self.audio_combo)

        # Subtitles
        self.sub_combo = QComboBox()
        self.sub_combo.setFixedWidth(120)
        self.sub_combo.setToolTip("Sous-titres")
        self.sub_combo.currentIndexChanged.connect(self._set_subtitle)
        self.sub_combo.hide()
        btn_row.addWidget(self.sub_combo)

        # Volume
        vol_lbl = QLabel("🔊")
        vol_lbl.setStyleSheet("background:transparent;font-size:14px;")
        btn_row.addWidget(vol_lbl)
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(self._set_volume)
        btn_row.addWidget(self.vol_slider)

        self.fs_btn = QPushButton("⛶")
        self.fs_btn.setObjectName("icon_btn")
        self.fs_btn.setFixedSize(32,32)
        self.fs_btn.setToolTip("Plein écran (F)")
        self.fs_btn.clicked.connect(self.toggle_fullscreen)
        btn_row.addWidget(self.fs_btn)

        cl.addLayout(btn_row)
        layout.addWidget(self.controls)

        # Progress timer
        self._pos_timer = QTimer(self)
        self._pos_timer.setInterval(500)
        self._pos_timer.timeout.connect(self._update_position)
        self._pos_timer.start()

    def play(self, url, name, is_live=False, resume_key=None):
        if not self.mp:
            return
        self.current_url = url
        self.current_name = name
        self.current_key = resume_key
        self.is_live = is_live
        self.now_lbl.setText(f"▶  {name}")
        media = self.instance.media_new(url)
        self.mp.set_media(media)
        if sys.platform == "win32":
            self.mp.set_hwnd(int(self.video_frame.winId()))
        elif sys.platform.startswith("linux"):
            self.mp.set_xwindow(int(self.video_frame.winId()))
        self.mp.play()
        self.play_btn.setText("⏸")
        # Show/hide controls based on type
        self.progress_slider.setVisible(not is_live)
        self.back_btn.setVisible(not is_live)
        self.fwd_btn.setVisible(not is_live)
        # Load tracks after a short delay
        QTimer.singleShot(2500, self._load_tracks)
        # Resume position
        if resume_key and not is_live:
            resume_pos = self.app_data.get("resume", {}).get(resume_key)
            if resume_pos:
                QTimer.singleShot(3000, lambda: self.mp.set_position(float(resume_pos)))
        self._resume_timer.start()
        self._show_controls()

    def _load_tracks(self):
        if not self.mp: return
        # Audio tracks
        self.audio_combo.blockSignals(True)
        self.audio_combo.clear()
        tracks = self.mp.audio_get_track_description()
        if tracks and len(tracks) > 1:
            for tid, tname in tracks:
                name = tname.decode() if isinstance(tname, bytes) else str(tname)
                self.audio_combo.addItem(f"🎵 {name}", tid)
            self.audio_combo.show()
        else:
            self.audio_combo.hide()
        self.audio_combo.blockSignals(False)
        # Subtitles
        self.sub_combo.blockSignals(True)
        self.sub_combo.clear()
        subs = self.mp.video_get_spu_description()
        self.sub_combo.addItem("🚫 Pas de sous-titres", -1)
        if subs:
            for sid, sname in subs:
                name = sname.decode() if isinstance(sname, bytes) else str(sname)
                self.sub_combo.addItem(f"💬 {name}", sid)
        if self.sub_combo.count() > 1:
            self.sub_combo.show()
        else:
            self.sub_combo.hide()
        self.sub_combo.blockSignals(False)

    def _set_audio(self, idx):
        if self.mp and self.audio_combo.count() > 0:
            tid = self.audio_combo.itemData(idx)
            if tid is not None: self.mp.audio_set_track(tid)

    def _set_subtitle(self, idx):
        if self.mp:
            sid = self.sub_combo.itemData(idx)
            if sid is not None: self.mp.video_set_spu(sid)

    def _set_volume(self, val):
        if self.mp: self.mp.audio_set_volume(val)

    def _seek(self, val):
        if self.mp: self.mp.set_position(val / 1000.0)

    def _skip(self, secs):
        if self.mp:
            t = self.mp.get_time()
            self.mp.set_time(max(0, t + secs * 1000))

    def toggle_pause(self):
        if not self.mp: return
        self.mp.pause()
        state = self.mp.get_state()
        self.play_btn.setText("▶" if state == vlc.State.Paused else "⏸")

    def stop(self):
        if self.mp:
            self._save_position()
            self.mp.stop()
            self.now_lbl.setText("")
            self.play_btn.setText("▶")
        self._resume_timer.stop()

    def _save_position(self):
        if self.mp and self.current_key and not self.is_live:
            pos = self.mp.get_position()
            if 0.01 < pos < 0.95:
                if "resume" not in self.app_data:
                    self.app_data["resume"] = {}
                self.app_data["resume"][self.current_key] = pos
                self.save_fn()

    def _on_end(self, event):
        if self.current_key:
            # Clear resume position when finished
            self.app_data.get("resume", {}).pop(self.current_key, None)
            self.save_fn()

    def _update_position(self):
        if not self.mp or self.is_live: return
        pos = self.mp.get_position()
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(int(pos * 1000))
        self.progress_slider.blockSignals(False)
        total = self.mp.get_length()
        cur = self.mp.get_time()
        if total > 0:
            self.time_lbl.setText(f"{self._fmt(cur)} / {self._fmt(total)}")

    def _fmt(self, ms):
        s = ms // 1000
        return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}" if s >= 3600 else f"{s//60:02d}:{s%60:02d}"

    def toggle_fullscreen(self):
        if not self._fullscreen:
            self._fs_win = QWidget()
            self._fs_win.setStyleSheet("background:#000;")
            self._fs_win.setWindowFlags(Qt.Window)
            fsl = QVBoxLayout(self._fs_win)
            fsl.setContentsMargins(0,0,0,0)
            # Move video_frame to fullscreen window
            self.video_frame.setParent(self._fs_win)
            fsl.addWidget(self.video_frame)
            if self.mp:
                self._fs_win.show()
                self._fs_win.showFullScreen()
                QTimer.singleShot(200, lambda: self.mp.set_hwnd(int(self.video_frame.winId())) if sys.platform=="win32" else None)
            self._fullscreen = True
            self._fs_win.keyPressEvent = self._fs_key
        else:
            self._exit_fullscreen()

    def _fs_key(self, e):
        if e.key() in (Qt.Key_Escape, Qt.Key_F):
            self._exit_fullscreen()
        elif e.key() == Qt.Key_Space:
            self.toggle_pause()
        elif e.key() == Qt.Key_Left:
            self._skip(-10)
        elif e.key() == Qt.Key_Right:
            self._skip(10)

    def _exit_fullscreen(self):
        if not self._fullscreen: return
        self.video_frame.setParent(self)
        self.layout().insertWidget(0, self.video_frame)
        if self.mp and sys.platform == "win32":
            QTimer.singleShot(200, lambda: self.mp.set_hwnd(int(self.video_frame.winId())))
        self._fs_win.close()
        self._fullscreen = False

    def _show_controls(self):
        self.controls.show()
        self._hide_timer.start(4000)

    def _auto_hide_controls(self):
        if self.mp and self.mp.is_playing():
            self.controls.hide()

    def mouseMoveEvent(self, e):
        self.controls.show()
        self._hide_timer.start(4000)
        super().mouseMoveEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space:
            self.toggle_pause()
        elif e.key() == Qt.Key_F:
            self.toggle_fullscreen()
        elif e.key() == Qt.Key_Left:
            self._skip(-10)
        elif e.key() == Qt.Key_Right:
            self._skip(10)
        elif e.key() == Qt.Key_Up:
            self.vol_slider.setValue(min(100, self.vol_slider.value() + 5))
        elif e.key() == Qt.Key_Down:
            self.vol_slider.setValue(max(0, self.vol_slider.value() - 5))
        elif e.key() == Qt.Key_Escape and self._fullscreen:
            self._exit_fullscreen()
        else:
            super().keyPressEvent(e)


# ─── RESUME DIALOG ───────────────────────────────────────────────────────────
class ResumeDialog(QDialog):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reprendre ?")
        self.setFixedSize(380, 180)
        self.setStyleSheet(STYLE)
        self.choice = "resume"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        lbl = QLabel(f"<b>{name}</b><br><span style='color:#aaa;font-size:12px;'>Vous avez déjà commencé ce contenu.</span>")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        btn_row = QHBoxLayout()
        resume_btn = QPushButton("▶ Reprendre")
        resume_btn.clicked.connect(lambda: (setattr(self, 'choice', 'resume'), self.accept()))
        restart_btn = QPushButton("⏮ Depuis le début")
        restart_btn.setObjectName("flat")
        restart_btn.clicked.connect(lambda: (setattr(self, 'choice', 'restart'), self.accept()))
        btn_row.addWidget(restart_btn)
        btn_row.addWidget(resume_btn)
        layout.addLayout(btn_row)


# ─── SERIES DETAIL PAGE ──────────────────────────────────────────────────────
class SeriesDetailPage(QWidget):
    play_episode = pyqtSignal(str, str, str)  # url, name, key
    back = pyqtSignal()

    def __init__(self, api, series_data, app_data, save_fn):
        super().__init__()
        self.api = api
        self.series_data = series_data
        self.app_data = app_data
        self.save_fn = save_fn
        self.info = {}
        self.current_season = None
        self._build_ui()
        self._load_info()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top = QFrame()
        top.setFixedHeight(50)
        top.setStyleSheet("background:#0a0a0a;border-bottom:1px solid #1a1a1a;")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 0, 12, 0)
        back_btn = QPushButton("← Retour")
        back_btn.setObjectName("flat")
        back_btn.setFixedHeight(32)
        back_btn.clicked.connect(self.back.emit)
        tl.addWidget(back_btn)
        self.title_lbl = QLabel("")
        self.title_lbl.setStyleSheet("font-size:15px;font-weight:bold;color:#fff;")
        tl.addWidget(self.title_lbl)
        tl.addStretch()
        # Favorite button
        self.fav_btn = QPushButton("☆ Favoris")
        self.fav_btn.setObjectName("flat")
        self.fav_btn.setFixedHeight(32)
        self.fav_btn.clicked.connect(self._toggle_fav)
        tl.addWidget(self.fav_btn)
        layout.addWidget(top)

        # Season selector
        season_bar = QFrame()
        season_bar.setFixedHeight(46)
        season_bar.setStyleSheet("background:#0d0d0d;border-bottom:1px solid #1a1a1a;")
        sl = QHBoxLayout(season_bar)
        sl.setContentsMargins(12, 4, 12, 4)
        sl.addWidget(QLabel("Saison :"))
        self.season_combo = QComboBox()
        self.season_combo.setFixedWidth(140)
        self.season_combo.currentIndexChanged.connect(self._load_season)
        sl.addWidget(self.season_combo)
        sl.addStretch()
        layout.addWidget(season_bar)

        self.episode_list = QListWidget()
        self.episode_list.itemDoubleClicked.connect(self._play_episode)
        layout.addWidget(self.episode_list)

    def _load_info(self):
        sid = self.series_data.get("series_id")
        self.title_lbl.setText(self.series_data.get("name", ""))
        self._update_fav_btn()
        w = Worker(self.api.get_series_info, sid)
        w.done.connect(self._on_info)
        w.start()
        self._w = w

    def _on_info(self, info):
        if not info: return
        self.info = info
        episodes = info.get("episodes", {})
        self.season_combo.blockSignals(True)
        self.season_combo.clear()
        for s in sorted(episodes.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            self.season_combo.addItem(f"Saison {s}", s)
        self.season_combo.blockSignals(False)
        if self.season_combo.count() > 0:
            self.season_combo.setCurrentIndex(0)
            self._load_season(0)

    def _load_season(self, idx):
        key = self.season_combo.itemData(idx)
        if not key: return
        self.current_season = key
        episodes = self.info.get("episodes", {}).get(key, [])
        self.episode_list.clear()
        resume_data = self.app_data.get("resume", {})
        for ep in episodes:
            num = ep.get("episode_num", "")
            title = ep.get("title", f"Épisode {num}")
            ep_key = f"ep_{ep.get('id')}"
            indicator = " 🔴" if ep_key in resume_data else ""
            item = QListWidgetItem(f"  Ép.{num} — {title}{indicator}")
            item.setData(Qt.UserRole, ep)
            self.episode_list.addItem(item)

    def _play_episode(self, item):
        ep = item.data(Qt.UserRole)
        if not ep: return
        sid = ep.get("id")
        ext = ep.get("container_extension", "mp4")
        url = self.api.episode_url(sid, ext)
        name = f"{self.series_data.get('name','')} — Ép.{ep.get('episode_num','')}"
        ep_key = f"ep_{sid}"
        self.play_episode.emit(url, name, ep_key)

    def _toggle_fav(self):
        favs = self.app_data.setdefault("favorites", [])
        sid = str(self.series_data.get("series_id", ""))
        entry = {"type": "series", "id": sid, "name": self.series_data.get("name", "")}
        existing = next((f for f in favs if f.get("id") == sid and f.get("type") == "series"), None)
        if existing:
            favs.remove(existing)
        else:
            favs.append(entry)
        self.save_fn()
        self._update_fav_btn()

    def _update_fav_btn(self):
        favs = self.app_data.get("favorites", [])
        sid = str(self.series_data.get("series_id", ""))
        is_fav = any(f.get("id") == sid and f.get("type") == "series" for f in favs)
        self.fav_btn.setText("★ Favoris" if is_fav else "☆ Favoris")


# ─── CONTENT PAGE (Live / VOD / Series) ──────────────────────────────────────
class ContentPage(QWidget):
    play_requested = pyqtSignal(str, str, bool, str)  # url, name, is_live, key
    open_series = pyqtSignal(object)

    def __init__(self, api, mode, app_data, save_fn):
        super().__init__()
        self.api = api
        self.mode = mode
        self.app_data = app_data
        self.save_fn = save_fn
        self.all_items = []
        self._build_ui()
        self._load_cats()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)

        # Categories sidebar
        left = QFrame()
        left.setFixedWidth(200)
        left.setStyleSheet("QFrame{background:#0a0a0a;border-right:1px solid #1a1a1a;}")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0,0,0,0)
        ll.setSpacing(0)
        cat_hdr = QLabel("  Catégories")
        cat_hdr.setFixedHeight(44)
        cat_hdr.setStyleSheet("color:#666;font-size:11px;font-weight:bold;letter-spacing:1px;border-bottom:1px solid #1a1a1a;padding-left:4px;")
        ll.addWidget(cat_hdr)
        self.cat_list = QListWidget()
        self.cat_list.setStyleSheet("""
            QListWidget{background:#0a0a0a;border:none;}
            QListWidget::item{padding:9px 12px;border-bottom:1px solid #111;font-size:12px;color:#999;}
            QListWidget::item:selected{background:#1a1a1a;color:#e50914;border-left:3px solid #e50914;}
            QListWidget::item:hover{background:#141414;color:#fff;}
        """)
        self.cat_list.currentRowChanged.connect(self._on_cat)
        ll.addWidget(self.cat_list)
        root.addWidget(left)

        # Right
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0)
        rl.setSpacing(0)

        # Search bar
        sb = QFrame()
        sb.setFixedHeight(54)
        sb.setStyleSheet("QFrame{background:#0d0d0d;border-bottom:1px solid #1a1a1a;}")
        sbl = QHBoxLayout(sb)
        sbl.setContentsMargins(12,7,12,7)
        icon = QLabel("🔍")
        icon.setStyleSheet("font-size:15px;")
        sbl.addWidget(icon)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher...")
        self.search.textChanged.connect(self._filter)
        sbl.addWidget(self.search)
        rl.addWidget(sb)

        self.list_w = QListWidget()
        self.list_w.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_w.customContextMenuRequested.connect(self._ctx_menu)
        self.list_w.itemDoubleClicked.connect(self._on_dblclick)
        rl.addWidget(self.list_w)

        self.status = QLabel("Chargement...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color:#444;font-size:13px;padding:30px;")
        rl.addWidget(self.status)

        root.addWidget(right)

    def _load_cats(self):
        fns = {"live": self.api.get_live_categories, "vod": self.api.get_vod_categories, "series": self.api.get_series_categories}
        w = Worker(fns[self.mode])
        w.done.connect(self._on_cats)
        w.start(); self._cw = w

    def _on_cats(self, cats):
        self.cat_list.clear()
        item = QListWidgetItem("  Tout afficher")
        self.cat_list.addItem(item)
        for c in (cats or []):
            it = QListWidgetItem(f"  {c.get('category_name','')}")
            it.setData(Qt.UserRole, c.get("category_id"))
            self.cat_list.addItem(it)
        self.cat_list.setCurrentRow(0)

    def _on_cat(self, row):
        if row < 0: return
        cid = self.cat_list.item(row).data(Qt.UserRole)
        self.list_w.clear()
        self.status.setText("Chargement...")
        fns = {"live": self.api.get_live_streams, "vod": self.api.get_vod_streams, "series": self.api.get_series}
        w = Worker(fns[self.mode], cid)
        w.done.connect(self._on_content)
        w.start(); self._lw = w

    def _on_content(self, items):
        self.all_items = items or []
        self.status.setText("")
        self._populate(self.all_items)

    def _populate(self, items):
        self.list_w.clear()
        favs = self.app_data.get("favorites", [])
        resume = self.app_data.get("resume", {})
        for s in items:
            name = s.get("name", s.get("title", "Sans titre"))
            sid = str(s.get("stream_id", s.get("series_id", "")))
            is_fav = any(f.get("id") == sid for f in favs)
            star = " ★" if is_fav else ""
            key = f"vod_{sid}" if self.mode == "vod" else f"ep_{sid}"
            dot = " 🔴" if key in resume else ""
            it = QListWidgetItem(f"  {name}{star}{dot}")
            it.setData(Qt.UserRole, s)
            self.list_w.addItem(it)
        if not items:
            self.status.setText("Aucun contenu.")

    def _filter(self, text):
        q = text.lower()
        self._populate([s for s in self.all_items if q in s.get("name", s.get("title","")).lower()])

    def _on_dblclick(self, item):
        data = item.data(Qt.UserRole)
        if not data: return
        if self.mode == "series":
            self.open_series.emit(data)
            return
        if self.mode == "live":
            url = self.api.live_url(data.get("stream_id"))
            name = data.get("name", "Live")
            self.play_requested.emit(url, name, True, "")
        elif self.mode == "vod":
            sid = data.get("stream_id")
            ext = data.get("container_extension", "mp4")
            url = self.api.vod_url(sid, ext)
            name = data.get("name", "Film")
            key = f"vod_{sid}"
            resume_pos = self.app_data.get("resume", {}).get(key)
            if resume_pos:
                dlg = ResumeDialog(name, self)
                if dlg.exec_():
                    if dlg.choice == "restart":
                        self.app_data["resume"].pop(key, None)
                        self.save_fn()
                    self.play_requested.emit(url, name, False, key)
            else:
                self.play_requested.emit(url, name, False, key)

    def _ctx_menu(self, pos):
        item = self.list_w.itemAt(pos)
        if not item: return
        data = item.data(Qt.UserRole)
        if not data: return
        sid = str(data.get("stream_id", data.get("series_id", "")))
        mode_label = {"live": "chaîne", "vod": "film", "series": "série"}[self.mode]
        favs = self.app_data.setdefault("favorites", [])
        is_fav = any(f.get("id") == sid for f in favs)
        menu = QMenu(self)
        fav_action = menu.addAction("★ Retirer des favoris" if is_fav else "☆ Ajouter aux favoris")
        action = menu.exec_(self.list_w.mapToGlobal(pos))
        if action == fav_action:
            if is_fav:
                self.app_data["favorites"] = [f for f in favs if f.get("id") != sid]
            else:
                favs.append({"type": self.mode, "id": sid, "name": data.get("name", data.get("title", ""))})
            self.save_fn()
            self._populate(self.all_items)


# ─── FAVORITES PAGE ───────────────────────────────────────────────────────────
class FavoritesPage(QWidget):
    play_requested = pyqtSignal(str, str, bool, str)
    open_series = pyqtSignal(object)

    def __init__(self, api, app_data, save_fn):
        super().__init__()
        self.api = api
        self.app_data = app_data
        self.save_fn = save_fn
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        hdr = QFrame()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet("background:#0d0d0d;border-bottom:1px solid #1a1a1a;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16,0,16,0)
        lbl = QLabel("★  Mes Favoris")
        lbl.setStyleSheet("font-size:15px;font-weight:bold;color:#fff;")
        hl.addWidget(lbl)
        hl.addStretch()
        layout.addWidget(hdr)
        self.list_w = QListWidget()
        self.list_w.itemDoubleClicked.connect(self._play)
        self.list_w.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_w.customContextMenuRequested.connect(self._ctx_menu)
        layout.addWidget(self.list_w)
        self.empty_lbl = QLabel("Aucun favori. Clic droit sur un contenu pour l'ajouter.")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setStyleSheet("color:#444;font-size:13px;padding:40px;")
        layout.addWidget(self.empty_lbl)

    def refresh(self):
        self.list_w.clear()
        favs = self.app_data.get("favorites", [])
        icons = {"live": "📺", "vod": "🎬", "series": "📂"}
        for f in favs:
            it = QListWidgetItem(f"  {icons.get(f.get('type',''),'▶')} {f.get('name','')}")
            it.setData(Qt.UserRole, f)
            self.list_w.addItem(it)
        self.empty_lbl.setVisible(len(favs) == 0)

    def _play(self, item):
        f = item.data(Qt.UserRole)
        if not f: return
        t = f.get("type")
        sid = f.get("id")
        name = f.get("name", "")
        if t == "live":
            self.play_requested.emit(self.api.live_url(sid), name, True, "")
        elif t == "vod":
            self.play_requested.emit(self.api.vod_url(sid), name, False, f"vod_{sid}")
        elif t == "series":
            self.open_series.emit({"series_id": sid, "name": name})

    def _ctx_menu(self, pos):
        item = self.list_w.itemAt(pos)
        if not item: return
        f = item.data(Qt.UserRole)
        menu = QMenu(self)
        rem = menu.addAction("🗑 Retirer des favoris")
        action = menu.exec_(self.list_w.mapToGlobal(pos))
        if action == rem:
            self.app_data["favorites"] = [x for x in self.app_data.get("favorites",[]) if x.get("id") != f.get("id")]
            self.save_fn()
            self.refresh()


# ─── PLAYLISTS MANAGER ────────────────────────────────────────────────────────
class PlaylistDialog(QDialog):
    def __init__(self, playlist=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter / Modifier une playlist")
        self.setFixedSize(420, 240)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(QLabel("Nom de la playlist :"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Famille, Travail...")
        if playlist: self.name_input.setText(playlist.get("name", ""))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("URL serveur :"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://server.com:8080")
        if playlist: self.url_input.setText(playlist.get("server", ""))
        layout.addWidget(self.url_input)
        row = QHBoxLayout()
        cancel = QPushButton("Annuler")
        cancel.setObjectName("flat")
        cancel.clicked.connect(self.reject)
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(save_btn)
        layout.addLayout(row)

    def get_data(self):
        return {"name": self.name_input.text().strip(), "server": self.url_input.text().strip()}


# ─── LOGIN PAGE ───────────────────────────────────────────────────────────────
class LoginPage(QWidget):
    login_ok = pyqtSignal(object, str)

    def __init__(self, app_data, save_fn):
        super().__init__()
        self.app_data = app_data
        self.save_fn = save_fn
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFixedWidth(480)
        card.setStyleSheet("QFrame{background:#111;border-radius:16px;border:1px solid #222;}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 36, 40, 36)
        cl.setSpacing(16)

        logo = QLabel("▶  IPTV Ultra")
        logo.setFont(QFont("Segoe UI", 28, QFont.Bold))
        logo.setStyleSheet("color:#e50914;border:none;background:transparent;")
        logo.setAlignment(Qt.AlignCenter)
        cl.addWidget(logo)

        sub = QLabel("Connexion Xtream Codes")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color:#555;font-size:13px;border:none;background:transparent;")
        cl.addWidget(sub)

        # Playlist selector
        pl_row = QHBoxLayout()
        self.pl_combo = QComboBox()
        self.pl_combo.setFixedHeight(38)
        self._refresh_playlists()
        self.pl_combo.currentIndexChanged.connect(self._on_pl_select)
        pl_row.addWidget(self.pl_combo)
        add_pl = QPushButton("+")
        add_pl.setFixedSize(38, 38)
        add_pl.setToolTip("Ajouter une playlist")
        add_pl.clicked.connect(self._add_playlist)
        pl_row.addWidget(add_pl)
        edit_pl = QPushButton("✏")
        edit_pl.setFixedSize(38, 38)
        edit_pl.setObjectName("flat")
        edit_pl.setToolTip("Modifier")
        edit_pl.clicked.connect(self._edit_playlist)
        pl_row.addWidget(edit_pl)
        del_pl = QPushButton("🗑")
        del_pl.setFixedSize(38, 38)
        del_pl.setObjectName("flat")
        del_pl.setToolTip("Supprimer")
        del_pl.clicked.connect(self._del_playlist)
        pl_row.addWidget(del_pl)
        cl.addLayout(pl_row)

        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("URL serveur  (ex: http://server.com:8080)")
        self.server_input.setFixedHeight(44)
        cl.addWidget(self.server_input)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Nom d'utilisateur")
        self.user_input.setFixedHeight(44)
        cl.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Mot de passe")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedHeight(44)
        self.pass_input.returnPressed.connect(self._login)
        cl.addWidget(self.pass_input)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet("color:#ff4444;font-size:12px;border:none;background:transparent;")
        self.err_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.err_lbl)

        self.login_btn = QPushButton("  Se connecter")
        self.login_btn.setFixedHeight(46)
        self.login_btn.clicked.connect(self._login)
        cl.addWidget(self.login_btn)

        self.prog = QProgressBar()
        self.prog.setRange(0, 0)
        self.prog.setFixedHeight(4)
        self.prog.hide()
        cl.addWidget(self.prog)

        main.addWidget(card, alignment=Qt.AlignCenter)

        # Dev credit
        credit = QLabel(DEVELOPER)
        credit.setAlignment(Qt.AlignCenter)
        credit.setStyleSheet("color:#333;font-size:11px;font-weight:bold;margin-top:10px;")
        main.addWidget(credit)

    def _refresh_playlists(self):
        self.pl_combo.blockSignals(True)
        self.pl_combo.clear()
        self.pl_combo.addItem("— Sélectionner une playlist —", None)
        for pl in self.app_data.get("playlists", []):
            self.pl_combo.addItem(pl.get("name", ""), pl)
        self.pl_combo.blockSignals(False)

    def _on_pl_select(self, idx):
        pl = self.pl_combo.itemData(idx)
        if pl:
            self.server_input.setText(pl.get("server", ""))
            self.user_input.setText(pl.get("username", ""))
            self.pass_input.setText(pl.get("password", ""))

    def _add_playlist(self):
        dlg = PlaylistDialog(parent=self)
        if dlg.exec_():
            d = dlg.get_data()
            if d["name"] and d["server"]:
                self.app_data.setdefault("playlists", []).append(d)
                self.save_fn()
                self._refresh_playlists()

    def _edit_playlist(self):
        pl = self.pl_combo.currentData()
        if not pl: return
        dlg = PlaylistDialog(pl, self)
        if dlg.exec_():
            d = dlg.get_data()
            pl.update(d)
            self.save_fn()
            self._refresh_playlists()

    def _del_playlist(self):
        pl = self.pl_combo.currentData()
        if not pl: return
        self.app_data["playlists"] = [p for p in self.app_data.get("playlists", []) if p is not pl]
        self.save_fn()
        self._refresh_playlists()

    def _login(self):
        server = self.server_input.text().strip().rstrip("/")
        user = self.user_input.text().strip()
        pwd = self.pass_input.text().strip()
        if not server or not user or not pwd:
            self.err_lbl.setText("Veuillez remplir tous les champs.")
            return
        if not server.startswith("http"):
            server = "http://" + server
        from urllib.parse import urlparse
        parsed = urlparse(server)
        servers = [server]
        if not parsed.port:
            servers += [server + ":8080", server + ":80"]
        # Save to current playlist
        pl = self.pl_combo.currentData()
        if pl:
            pl.update({"server": server, "username": user, "password": pwd})
            self.save_fn()
        self.err_lbl.setText("")
        self.login_btn.setEnabled(False)
        self.prog.show()
        self._worker = LoginWorker(servers, user, pwd)
        self._worker.ok.connect(self._on_ok)
        self._worker.fail.connect(self._on_fail)
        self._worker.start()

    def _on_ok(self, api, info):
        self.prog.hide()
        self.login_btn.setEnabled(True)
        self.login_ok.emit(api, self.server_input.text().strip())

    def _on_fail(self):
        self.prog.hide()
        self.login_btn.setEnabled(True)
        self.err_lbl.setText("Connexion échouée. Vérifiez l'URL et vos identifiants.")


# ─── MAIN WINDOW ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, api, app_data, save_fn):
        super().__init__()
        self.api = api
        self.app_data = app_data
        self.save_fn = save_fn
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(make_icon())
        self.setMinimumSize(1200, 750)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Topbar
        top = QFrame()
        top.setFixedHeight(56)
        top.setStyleSheet("QFrame{background:#0a0a0a;border-bottom:1px solid #1a1a1a;}")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(20, 0, 20, 0)
        logo = QLabel("▶  IPTV Ultra")
        logo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo.setStyleSheet("color:#e50914;background:transparent;border:none;")
        tl.addWidget(logo)
        tl.addStretch()
        self.clock = ClockLabel()
        tl.addWidget(self.clock)
        tl.addSpacing(20)
        logout = QPushButton("Déconnexion")
        logout.setObjectName("flat")
        logout.setFixedHeight(34)
        logout.clicked.connect(self._logout)
        tl.addWidget(logout)
        root.addWidget(top)

        # Body
        body = QHBoxLayout()
        body.setContentsMargins(0,0,0,0)
        body.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(170)
        sidebar.setStyleSheet("QFrame{background:#0a0a0a;border-right:1px solid #1a1a1a;}")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 16, 0, 16)
        sl.setSpacing(3)
        self._nav_btns = []
        for label, idx in [("📺  Live", 0), ("🎬  Films", 1), ("📂  Séries", 2), ("★  Favoris", 3)]:
            btn = QPushButton(label)
            btn.setStyleSheet(NAV_STYLE)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._switch(i))
            sl.addWidget(btn)
            self._nav_btns.append(btn)
        sl.addStretch()
        body.addWidget(sidebar)

        # Main area: stack + player
        main_area = QVBoxLayout()
        main_area.setContentsMargins(0,0,0,0)
        main_area.setSpacing(0)

        self.stack = QStackedWidget()
        self.live_page = ContentPage(self.api, "live", self.app_data, self.save_fn)
        self.live_page.play_requested.connect(self._play)
        self.vod_page = ContentPage(self.api, "vod", self.app_data, self.save_fn)
        self.vod_page.play_requested.connect(self._play)
        self.series_page = ContentPage(self.api, "series", self.app_data, self.save_fn)
        self.series_page.open_series.connect(self._open_series)
        self.favs_page = FavoritesPage(self.api, self.app_data, self.save_fn)
        self.favs_page.play_requested.connect(self._play)
        self.favs_page.open_series.connect(self._open_series)

        self.stack.addWidget(self.live_page)
        self.stack.addWidget(self.vod_page)
        self.stack.addWidget(self.series_page)
        self.stack.addWidget(self.favs_page)
        main_area.addWidget(self.stack, stretch=3)

        # Splitter for player
        self.player = VideoPlayer(self.app_data, self.save_fn)
        self.player.setMinimumHeight(240)
        self.player.setMaximumHeight(400)
        main_area.addWidget(self.player, stretch=2)

        body.addLayout(main_area)
        root.addLayout(body)

        # Dev credit
        credit_bar = QFrame()
        credit_bar.setFixedHeight(22)
        credit_bar.setStyleSheet("background:#050505;border-top:1px solid #111;")
        cbl = QHBoxLayout(credit_bar)
        cbl.setContentsMargins(0,0,0,0)
        credit_lbl = QLabel(DEVELOPER)
        credit_lbl.setAlignment(Qt.AlignCenter)
        credit_lbl.setStyleSheet("color:#2a2a2a;font-size:10px;font-weight:bold;background:transparent;")
        cbl.addWidget(credit_lbl)
        root.addWidget(credit_bar)

        self._switch(0)

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 3:
            self.favs_page.refresh()
        for i, btn in enumerate(self._nav_btns):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn); btn.style().polish(btn)

    def _play(self, url, name, is_live, key):
        self.player.play(url, name, is_live, key or None)
        self.player.setFocus()

    def _open_series(self, data):
        page = SeriesDetailPage(self.api, data, self.app_data, self.save_fn)
        page.play_episode.connect(lambda url, name, key: self._play(url, name, False, key))
        page.back.connect(lambda: self.stack.removeWidget(page))
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

    def _logout(self):
        self.player.stop()
        self.close()
        self._relaunch()

    def _relaunch(self):
    self._login_win = QMainWindow()
    self._login_win.setWindowTitle(f"{APP_NAME} — Connexion")
    self._login_win.setWindowIcon(make_icon())
    self._login_win.setMinimumSize(640, 520)
    self._login_win.setStyleSheet(STYLE)

    lp = LoginPage(self.app_data, self.save_fn)

    def go_main(api, s):
        self._mw = MainWindow(api, self.app_data, self.save_fn)
        self._mw.setStyleSheet(STYLE)
        self._mw.show()
        self._login_win.hide()

    lp.login_ok.connect(go_main)
    self._login_win.setCentralWidget(lp)
    self._login_win.show()

    def closeEvent(self, e):
        self.player.stop()
        e.accept()

    def keyPressEvent(self, e):
        self.player.keyPressEvent(e)


# ─── ENTRY ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app_data = load_data()

    def save():
        save_data(app_data)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(make_icon())

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(13,13,13))
    pal.setColor(QPalette.WindowText, QColor(255,255,255))
    pal.setColor(QPalette.Base, QColor(17,17,17))
    pal.setColor(QPalette.Text, QColor(255,255,255))
    pal.setColor(QPalette.Button, QColor(30,30,30))
    pal.setColor(QPalette.ButtonText, QColor(255,255,255))
    pal.setColor(QPalette.Highlight, QColor(229,9,20))
    pal.setColor(QPalette.HighlightedText, QColor(255,255,255))
    app.setPalette(pal)

    win = QMainWindow()
    win.setWindowTitle(f"{APP_NAME} — Connexion")
    win.setWindowIcon(make_icon())
    win.setMinimumSize(640, 520)
    win.setStyleSheet(STYLE)
    lp = LoginPage(app_data, save)

    def on_login(api, server):
    app._mw = MainWindow(api, app_data, save)
    app._mw.setStyleSheet(STYLE)
    app._mw.show()
    win.hide()

    lp.login_ok.connect(on_login)
win.setCentralWidget(lp)
win.show()
sys.exit(app.exec_())
