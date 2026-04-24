
import sys
import os
import requests
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QStackedWidget, QFrame, QMessageBox, QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False

# ─── STYLES ──────────────────────────────────────────────────────────────────
MAIN_STYLE = """
QMainWindow, QWidget {
    background-color: #0d0d0d;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QLabel { color: #ffffff; }
QLineEdit {
    background-color: #1e1e1e;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px 14px;
    color: #ffffff;
    font-size: 14px;
}
QLineEdit:focus { border: 1px solid #e50914; }
QPushButton {
    background-color: #e50914;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: bold;
}
QPushButton:hover { background-color: #ff1a1a; }
QPushButton:pressed { background-color: #b0070f; }
QPushButton#secondaryBtn {
    background-color: #1e1e1e;
    border: 1px solid #444;
}
QPushButton#secondaryBtn:hover {
    background-color: #2a2a2a;
    border: 1px solid #e50914;
}
QPushButton#stopBtn {
    background-color: #333;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton#stopBtn:hover { background-color: #e50914; }
QListWidget {
    background-color: #111111;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 12px 16px;
    border-bottom: 1px solid #1a1a1a;
    color: #cccccc;
    font-size: 13px;
}
QListWidget::item:selected { background-color: #e50914; color: white; }
QListWidget::item:hover { background-color: #1e1e1e; color: white; }
QScrollBar:vertical {
    background: #111; width: 6px; border-radius: 3px;
}
QScrollBar::handle:vertical { background: #444; border-radius: 3px; }
QScrollBar::handle:vertical:hover { background: #e50914; }
QProgressBar {
    background-color: #1e1e1e;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk { background-color: #e50914; border-radius: 4px; }
"""

NAV_BTN_STYLE = """
QPushButton {
    background-color: transparent;
    color: #888888;
    border: none;
    border-radius: 8px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: normal;
    text-align: left;
}
QPushButton:hover { background-color: #1a1a1a; color: #ffffff; }
QPushButton[active="true"] {
    background-color: #1a1a1a;
    color: #e50914;
    font-weight: bold;
    border-left: 3px solid #e50914;
}
"""

# ─── XTREAM API ───────────────────────────────────────────────────────────────
class XtreamAPI:
    def __init__(self, server, username, password):
        self.server = server.rstrip("/")
        self.username = username
        self.password = password
        self.base = f"{self.server}/player_api.php?username={username}&password={password}"

    def get_info(self):
        try:
            r = requests.get(self.base, timeout=10)
            return r.json()
        except:
            return None

    def get_live_categories(self):
        try:
            r = requests.get(f"{self.base}&action=get_live_categories", timeout=15)
            return r.json()
        except:
            return []

    def get_live_streams(self, category_id=None):
        try:
            url = f"{self.base}&action=get_live_streams"
            if category_id:
                url += f"&category_id={category_id}"
            r = requests.get(url, timeout=20)
            return r.json()
        except:
            return []

    def get_vod_categories(self):
        try:
            r = requests.get(f"{self.base}&action=get_vod_categories", timeout=15)
            return r.json()
        except:
            return []

    def get_vod_streams(self, category_id=None):
        try:
            url = f"{self.base}&action=get_vod_streams"
            if category_id:
                url += f"&category_id={category_id}"
            r = requests.get(url, timeout=20)
            return r.json()
        except:
            return []

    def get_series_categories(self):
        try:
            r = requests.get(f"{self.base}&action=get_series_categories", timeout=15)
            return r.json()
        except:
            return []

    def get_series(self, category_id=None):
        try:
            url = f"{self.base}&action=get_series"
            if category_id:
                url += f"&category_id={category_id}"
            r = requests.get(url, timeout=20)
            return r.json()
        except:
            return []

    def get_series_info(self, series_id):
        try:
            r = requests.get(f"{self.base}&action=get_series_info&series_id={series_id}", timeout=15)
            return r.json()
        except:
            return {}

    def get_live_url(self, stream_id):
        return f"{self.server}/live/{self.username}/{self.password}/{stream_id}.ts"

    def get_vod_url(self, stream_id, container_extension="mp4"):
        return f"{self.server}/movie/{self.username}/{self.password}/{stream_id}.{container_extension}"

    def get_series_episode_url(self, stream_id, container_extension="mp4"):
        return f"{self.server}/series/{self.username}/{self.password}/{stream_id}.{container_extension}"


# ─── WORKERS ─────────────────────────────────────────────────────────────────
class LoadWorker(QThread):
    finished = pyqtSignal(list)
    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args
    def run(self):
        try:
            result = self.func(*self.args)
            self.finished.emit(result if result else [])
        except:
            self.finished.emit([])

class LoginWorker(QThread):
    success = pyqtSignal(dict)
    failure = pyqtSignal(str)
    def __init__(self, api):
        super().__init__()
        self.api = api
    def run(self):
        info = self.api.get_info()
        if info and "user_info" in info:
            self.success.emit(info)
        else:
            self.failure.emit("Connexion échouée. Vérifiez vos identifiants.")


# ─── VLC PLAYER WIDGET ───────────────────────────────────────────────────────
class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #000000;")
        self.setMinimumHeight(300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video frame
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: #000000;")
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_frame)

        # Controls bar
        controls = QFrame()
        controls.setFixedHeight(50)
        controls.setStyleSheet("background-color: #0a0a0a; border-top: 1px solid #1a1a1a;")
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(16, 0, 16, 0)

        self.now_playing = QLabel("Aucune lecture en cours")
        self.now_playing.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        ctrl_layout.addWidget(self.now_playing)
        ctrl_layout.addStretch()

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setObjectName("stopBtn")
        self.pause_btn.setFixedHeight(32)
        self.pause_btn.clicked.connect(self.toggle_pause)
        ctrl_layout.addWidget(self.pause_btn)

        stop_btn = QPushButton("⏹ Stop")
        stop_btn.setObjectName("stopBtn")
        stop_btn.setFixedHeight(32)
        stop_btn.clicked.connect(self.stop)
        ctrl_layout.addWidget(stop_btn)

        layout.addWidget(controls)

        self.instance = None
        self.media_player = None
        if VLC_AVAILABLE:
            self.instance = vlc.Instance(
                "--no-xlib",
                "--network-caching=1500",
                "--live-caching=1500",
                "--demux=ts",
                "--ts-trust-pcr",
            )
            self.media_player = self.instance.media_player_new()

    def play(self, url, name=""):
        if not VLC_AVAILABLE or not self.media_player:
            QMessageBox.warning(self, "Erreur", "VLC non disponible dans ce build.")
            return
        self.now_playing.setText(f"▶  {name}")
        media = self.instance.media_new(url)
        self.media_player.set_media(media)
        if sys.platform == "win32":
            self.media_player.set_hwnd(int(self.video_frame.winId()))
        elif sys.platform == "linux":
            self.media_player.set_xwindow(int(self.video_frame.winId()))
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(int(self.video_frame.winId()))
        self.media_player.play()
        self.pause_btn.setText("⏸ Pause")

    def toggle_pause(self):
        if self.media_player:
            self.media_player.pause()
            state = self.media_player.get_state()
            if state == vlc.State.Paused:
                self.pause_btn.setText("▶ Reprendre")
            else:
                self.pause_btn.setText("⏸ Pause")

    def stop(self):
        if self.media_player:
            self.media_player.stop()
            self.now_playing.setText("Aucune lecture en cours")
            self.pause_btn.setText("⏸ Pause")


# ─── LOGIN PAGE ───────────────────────────────────────────────────────────────
class LoginPage(QWidget):
    login_success = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFixedWidth(460)
        card.setStyleSheet("QFrame { background-color: #111111; border-radius: 16px; border: 1px solid #222; }")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 40, 40, 40)
        cl.setSpacing(18)

        logo = QLabel("▶  IPTV Player Pro")
        logo.setFont(QFont("Segoe UI", 26, QFont.Bold))
        logo.setStyleSheet("color: #e50914; border: none; background: transparent;")
        logo.setAlignment(Qt.AlignCenter)
        cl.addWidget(logo)

        sub = QLabel("Connexion Xtream Codes")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #666; font-size: 13px; border: none; background: transparent;")
        cl.addWidget(sub)
        cl.addSpacing(6)

        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("URL serveur  (ex: http://server.com:8080)")
        self.server_input.setFixedHeight(46)
        cl.addWidget(self.server_input)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Nom d'utilisateur")
        self.user_input.setFixedHeight(46)
        cl.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Mot de passe")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedHeight(46)
        self.pass_input.returnPressed.connect(self._do_login)
        cl.addWidget(self.pass_input)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #ff4444; font-size: 12px; border: none; background: transparent;")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.error_lbl)

        self.login_btn = QPushButton("  Se connecter")
        self.login_btn.setFixedHeight(48)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._do_login)
        cl.addWidget(self.login_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        cl.addWidget(self.progress)

        main.addWidget(card, alignment=Qt.AlignCenter)

    def _do_login(self):
        server = self.server_input.text().strip()
        user = self.user_input.text().strip()
        pwd = self.pass_input.text().strip()
        if not server or not user or not pwd:
            self.error_lbl.setText("Veuillez remplir tous les champs.")
            return
        self.error_lbl.setText("")
        self.login_btn.setEnabled(False)
        self.progress.show()
        api = XtreamAPI(server, user, pwd)
        self.worker = LoginWorker(api)
        self.worker.success.connect(lambda info: self._on_success(api, info))
        self.worker.failure.connect(self._on_failure)
        self.worker.start()

    def _on_success(self, api, info):
        self.progress.hide()
        self.login_btn.setEnabled(True)
        self.login_success.emit(api)

    def _on_failure(self, msg):
        self.progress.hide()
        self.login_btn.setEnabled(True)
        self.error_lbl.setText(msg)


# ─── CONTENT PAGE ─────────────────────────────────────────────────────────────
class ContentPage(QWidget):
    play_requested = pyqtSignal(str, str)

    def __init__(self, api, mode="live"):
        super().__init__()
        self.api = api
        self.mode = mode
        self.all_items = []
        self._build_ui()
        self._load_categories()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar categories
        left = QFrame()
        left.setFixedWidth(210)
        left.setStyleSheet("QFrame { background-color: #0a0a0a; border-right: 1px solid #1a1a1a; }")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        cat_title = QLabel("  Catégories")
        cat_title.setFixedHeight(46)
        cat_title.setStyleSheet("color: #888; font-size: 11px; font-weight: bold; letter-spacing: 1px; background: #0a0a0a; border-bottom: 1px solid #1a1a1a; padding-left: 4px;")
        ll.addWidget(cat_title)

        self.cat_list = QListWidget()
        self.cat_list.setStyleSheet("""
            QListWidget { background: #0a0a0a; border: none; }
            QListWidget::item { padding: 10px 14px; border-bottom: 1px solid #111; font-size: 12px; color: #aaa; }
            QListWidget::item:selected { background: #1a1a1a; color: #e50914; border-left: 3px solid #e50914; }
            QListWidget::item:hover { background: #141414; color: #fff; }
        """)
        self.cat_list.currentRowChanged.connect(self._on_cat_changed)
        ll.addWidget(self.cat_list)
        root.addWidget(left)

        # Right
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # Search
        sb = QFrame()
        sb.setFixedHeight(58)
        sb.setStyleSheet("QFrame { background: #0d0d0d; border-bottom: 1px solid #1a1a1a; }")
        sbl = QHBoxLayout(sb)
        sbl.setContentsMargins(14, 8, 14, 8)
        sbl.addWidget(QLabel("🔍"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher...")
        self.search.setStyleSheet("QLineEdit { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 18px; padding: 7px 14px; font-size: 13px; }")
        self.search.textChanged.connect(self._filter)
        sbl.addWidget(self.search)
        rl.addWidget(sb)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        rl.addWidget(self.list_widget)

        self.status = QLabel("Chargement...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: #555; font-size: 13px; padding: 20px;")
        rl.addWidget(self.status)

        root.addWidget(right)

    def _load_categories(self):
        funcs = {"live": self.api.get_live_categories, "vod": self.api.get_vod_categories, "series": self.api.get_series_categories}
        self._cat_worker = LoadWorker(funcs[self.mode])
        self._cat_worker.finished.connect(self._on_cats_loaded)
        self._cat_worker.start()

    def _on_cats_loaded(self, cats):
        self.cat_list.clear()
        self.cat_list.addItem(QListWidgetItem("  Tout afficher"))
        for c in cats:
            item = QListWidgetItem(f"  {c.get('category_name', '')}")
            item.setData(Qt.UserRole, c.get("category_id"))
            self.cat_list.addItem(item)
        self.cat_list.setCurrentRow(0)

    def _on_cat_changed(self, row):
        if row < 0:
            return
        cat_id = self.cat_list.item(row).data(Qt.UserRole)
        self.list_widget.clear()
        self.status.setText("Chargement...")
        funcs = {"live": self.api.get_live_streams, "vod": self.api.get_vod_streams, "series": self.api.get_series}
        self._content_worker = LoadWorker(funcs[self.mode], cat_id)
        self._content_worker.finished.connect(self._on_content_loaded)
        self._content_worker.start()

    def _on_content_loaded(self, items):
        self.all_items = items
        self.status.setText("")
        self._populate(items)

    def _populate(self, items):
        self.list_widget.clear()
        for s in items:
            name = s.get("name", s.get("title", "Sans titre"))
            item = QListWidgetItem(f"  {name}")
            item.setData(Qt.UserRole, s)
            self.list_widget.addItem(item)
        if not items:
            self.status.setText("Aucun contenu trouvé.")

    def _filter(self, text):
        filtered = [s for s in self.all_items if text.lower() in s.get("name", s.get("title", "")).lower()]
        self._populate(filtered)

    def _on_double_click(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        if self.mode == "live":
            url = self.api.get_live_url(data.get("stream_id"))
            name = data.get("name", "Live")
        elif self.mode == "vod":
            url = self.api.get_vod_url(data.get("stream_id"), data.get("container_extension", "mp4"))
            name = data.get("name", "Film")
        else:
            url = None
            name = data.get("name", "Série")
        if url:
            self.play_requested.emit(url, name)


# ─── MAIN WINDOW ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.setWindowTitle("IPTV Player Pro")
        self.setMinimumSize(1200, 720)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Topbar
        topbar = QFrame()
        topbar.setFixedHeight(58)
        topbar.setStyleSheet("QFrame { background-color: #0a0a0a; border-bottom: 1px solid #1a1a1a; }")
        tbl = QHBoxLayout(topbar)
        tbl.setContentsMargins(20, 0, 20, 0)
        logo = QLabel("▶  IPTV Player Pro")
        logo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo.setStyleSheet("color: #e50914; background: transparent; border: none;")
        tbl.addWidget(logo)
        tbl.addStretch()
        logout = QPushButton("Déconnexion")
        logout.setObjectName("secondaryBtn")
        logout.setFixedHeight(34)
        logout.setCursor(Qt.PointingHandCursor)
        logout.clicked.connect(self._logout)
        tbl.addWidget(logout)
        root.addWidget(topbar)

        # Body
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sidebar nav
        sidebar = QFrame()
        sidebar.setFixedWidth(175)
        sidebar.setStyleSheet("QFrame { background-color: #0a0a0a; border-right: 1px solid #1a1a1a; }")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 20, 0, 20)
        sl.setSpacing(4)

        self.nav_btns = []
        for label, idx in [("📺  Chaînes Live", 0), ("🎬  Films", 1), ("📂  Séries", 2)]:
            btn = QPushButton(label)
            btn.setStyleSheet(NAV_BTN_STYLE)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._switch(i))
            sl.addWidget(btn)
            self.nav_btns.append(btn)
        sl.addStretch()
        body.addWidget(sidebar)

        # Main content: stack + player
        content_area = QVBoxLayout()
        content_area.setContentsMargins(0, 0, 0, 0)
        content_area.setSpacing(0)

        self.stack = QStackedWidget()
        self.live_page = ContentPage(api, "live")
        self.live_page.play_requested.connect(self._play)
        self.vod_page = ContentPage(api, "vod")
        self.vod_page.play_requested.connect(self._play)
        self.series_page = ContentPage(api, "series")
        self.series_page.play_requested.connect(self._play)
        self.stack.addWidget(self.live_page)
        self.stack.addWidget(self.vod_page)
        self.stack.addWidget(self.series_page)
        content_area.addWidget(self.stack, stretch=1)

        # Embedded player
        self.player = VideoPlayer()
        self.player.setFixedHeight(340)
        content_area.addWidget(self.player)

        body.addLayout(content_area)
        root.addLayout(body)
        self._switch(0)

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_btns):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _play(self, url, name):
        self.player.play(url, name)

    def _logout(self):
        if self.player.media_player:
            self.player.media_player.stop()
        self.close()
        self._login_win = QMainWindow()
        lp = LoginPage()
        lp.login_success.connect(self._reopen)
        self._login_win.setCentralWidget(lp)
        self._login_win.setWindowTitle("IPTV Player Pro - Connexion")
        self._login_win.setMinimumSize(600, 500)
        self._login_win.setStyleSheet(MAIN_STYLE)
        self._login_win.show()

    def _reopen(self, api):
        self._login_win.close()
        w = MainWindow(api)
        w.setStyleSheet(MAIN_STYLE)
        w.show()
        self._new = w

    def closeEvent(self, event):
        if self.player.media_player:
            self.player.media_player.stop()
        event.accept()


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(MAIN_STYLE)

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(13, 13, 13))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(17, 17, 17))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(30, 30, 30))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.Highlight, QColor(229, 9, 20))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    win = QMainWindow()
    lp = LoginPage()
    lp.login_success.connect(lambda api: (win.close(), setattr(app, '_main', MainWindow(api))) or app._main.setStyleSheet(MAIN_STYLE) or app._main.show())
    win.setCentralWidget(lp)
    win.setWindowTitle("IPTV Player Pro - Connexion")
    win.setMinimumSize(600, 500)
    win.setStyleSheet(MAIN_STYLE)
    win.show()

    sys.exit(app.exec_())
