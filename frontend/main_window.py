from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QMainWindow,
    QVBoxLayout, QWidget, QLabel, QPushButton, QSizePolicy
)

from backend.config import APP_NAME, APP_VERSION
from backend.renderer import Renderer
from backend.queue_manager import QueueState
from frontend.sidebar_left import SidebarLeft
from frontend.sidebar_right import SidebarRight
from frontend.render_panel import RenderPanel
from frontend.theme import apply_theme

GITHUB_PROFILE = "https://github.com/hndrapratamaa"
GITHUB_ISSUES  = "https://github.com/hndrapratamaa/Profile/issues"
WEB_PROFILE    = "https://hndrapratamaa.github.io"


def _sp(w: QWidget, h_pol, v_pol) -> QWidget:
    w.setSizePolicy(h_pol, v_pol)
    return w


def _card() -> QFrame:
    f = QFrame()
    f.setProperty("role", "card")
    f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return f


class MainWindow(QMainWindow):
    sig_log      = Signal(str)
    sig_progress = Signal(int, int, float, float, float, float, float)
    sig_state    = Signal(object)

    def __init__(self, renderer: Renderer) -> None:
        super().__init__()
        self.renderer   = renderer
        self._dark_mode = True
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1100, 700)
        self.resize(1340, 860)
        
        self.sidebar_left  = SidebarLeft(self.renderer)
        self.sidebar_right = SidebarRight()
        self.render_panel  = RenderPanel(self.renderer)

        self._build_layout()
        self._wire_signals()
        
        apply_theme(self, dark=True)
        self.renderer.initialise()
        self.render_panel.update_state(self.renderer.get_state())

    def _build_layout(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_lyt = QVBoxLayout(root)
        root_lyt.setContentsMargins(12, 12, 12, 12)
        root_lyt.setSpacing(10)

        root_lyt.addLayout(self._make_topbar())

        # Pake QHBoxLayout murni biar sisa garis seret splitter ilang total blay!
        main_body_lyt = QHBoxLayout()
        main_body_lyt.setContentsMargins(0, 0, 0, 0)
        main_body_lyt.setSpacing(10)

        left_container = QWidget()
        left_lyt = QVBoxLayout(left_container)
        left_lyt.setContentsMargins(0, 0, 0, 0)
        left_lyt.setSpacing(10)

        self._assemble_left_layout(left_lyt)

        main_body_lyt.addWidget(left_container, stretch=1)
        main_body_lyt.addWidget(self._make_preview_col(), stretch=0)

        root_lyt.addLayout(main_body_lyt, stretch=1)

        # Re-map text tombol render panel bawaan ke bahasa Depok
        self.render_panel.btn_start.setText("[MULAI RENDER]")
        self.render_panel.btn_pause.setText("[BENTAR]")
        self.render_panel.btn_continue.setText("[LANJUT]")
        self.render_panel.btn_stop.setText("[BERENTI]")
        self.render_panel.btn_refresh.setText("[SEGERIN]")

        self.render_panel.btn_start.clicked.connect(self._start_render)
        self.render_panel.btn_pause.clicked.connect(self._pause_render)
        self.render_panel.btn_continue.clicked.connect(self._continue_render)
        self.render_panel.btn_stop.clicked.connect(self._stop_render)
        self.render_panel.btn_refresh.clicked.connect(self._refresh_app)

    def _make_topbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)

        lbl = QLabel(f"{APP_NAME} software by hndrapratamaa")
        lbl.setProperty("role", "appTitle")
        _sp(lbl, QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.btn_theme = QPushButton("🌙 Gelap")
        self.btn_theme.setCheckable(True)
        self.btn_theme.setChecked(True)
        self.btn_theme.setFixedWidth(100)
        self.btn_theme.clicked.connect(self._toggle_theme)

        btn_github = QPushButton("⌥ GitHub")
        btn_github.setFixedWidth(100)
        btn_report = QPushButton("🐛 Laporkan Masalah")
        btn_report.setFixedWidth(150)
        btn_web    = QPushButton("🌐 Web Gua")
        btn_web.setFixedWidth(110)

        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_PROFILE)))
        btn_report.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_ISSUES)))
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(WEB_PROFILE)))

        bar.addWidget(lbl)
        bar.addStretch()
        bar.addWidget(btn_web)
        bar.addWidget(btn_report)
        bar.addWidget(btn_github)
        bar.addWidget(self.btn_theme)
        return bar

    def _assemble_left_layout(self, parent_lyt: QVBoxLayout) -> None:
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(self._make_render_monitor(), stretch=1)
        top_row.addWidget(self._make_terminal_panel(), stretch=1)

        ctrl_widget = QWidget()
        ctrl_lyt = QHBoxLayout(ctrl_widget)
        ctrl_lyt.setContentsMargins(0, 2, 0, 2)
        ctrl_lyt.setSpacing(8)
        
        self.btn_tiktok = QPushButton("[AUTO UP]")
        self.btn_tiktok.setProperty("role", "tiktokBtn")
        
        control_buttons = [
            self.render_panel.btn_start,
            self.render_panel.btn_pause,
            self.render_panel.btn_continue,
            self.render_panel.btn_stop,
            self.render_panel.btn_refresh,
            self.btn_tiktok
        ]
        
        for btn in control_buttons:
            _sp(btn, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(38)
            ctrl_lyt.addWidget(btn)

        bot_row = QHBoxLayout()
        bot_row.setSpacing(10)
        bot_row.addWidget(self._make_input_panel(), stretch=1)
        bot_row.addWidget(self._make_output_panel(), stretch=1)

        parent_lyt.addLayout(top_row, stretch=35)
        parent_lyt.addWidget(ctrl_widget, stretch=0)
        parent_lyt.addLayout(bot_row, stretch=65)

    def _make_render_monitor(self) -> QFrame:
        card = _card()
        lyt = QVBoxLayout(card)
        lyt.setContentsMargins(14, 14, 14, 14)
        lyt.setSpacing(10)

        hdr = QHBoxLayout()
        lbl = QLabel("STATUS RENDER")
        lbl.setProperty("role", "sectionTitle")
        hdr.addWidget(lbl)
        hdr.addStretch()

        self.lbl_status = QLabel("SIAP")
        self.lbl_status.setProperty("role", "statusReady")
        hdr.addWidget(self.lbl_status)
        lyt.addLayout(hdr)

        lyt.addLayout(self.render_panel.stats_grid)
        lyt.addWidget(self.render_panel.pb_segment)
        lyt.addWidget(self.render_panel.pb_overall)
        lyt.addStretch(1)
        return card

    def _make_terminal_panel(self) -> QFrame:
        card = _card()
        lyt = QVBoxLayout(card)
        lyt.setContentsMargins(14, 14, 14, 14)
        lyt.setSpacing(10)

        hdr = QHBoxLayout()
        lbl = QLabel("LOG TERMINAL")
        lbl.setProperty("role", "sectionTitle")
        hdr.addWidget(lbl)
        hdr.addStretch()
        
        # Override teks tombol internal log render_panel
        self.render_panel.btn_copy_log.setText("Salin")
        self.render_panel.btn_clear_log.setText("Bersihin")
        
        for btn in [self.render_panel.btn_copy_log, self.render_panel.btn_clear_log]:
            btn.setFixedSize(75, 26)
            hdr.addWidget(btn)
            
        lyt.addLayout(hdr)

        _sp(self.render_panel.log_output, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lyt.addWidget(self.render_panel.log_output, stretch=1)
        return card

    def _make_input_panel(self) -> QFrame:
        card = _card()
        lyt = QVBoxLayout(card)
        lyt.setContentsMargins(14, 14, 14, 14)
        lyt.setSpacing(10)

        lbl = QLabel("FOLDER MENTAH")
        lbl.setProperty("role", "sectionTitle")
        lyt.addWidget(lbl)

        _sp(self.sidebar_left.list_widget, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lyt.addWidget(self.sidebar_left.list_widget, stretch=1)

        btn_row = QHBoxLayout()
        self.sidebar_left.btn_import.setText("[IMPORT]")
        self.sidebar_left.btn_delete.setText("[APUS]")
        self.sidebar_left.btn_delete.setProperty("role", "dangerBtn")
        
        for btn in [self.sidebar_left.btn_import, self.sidebar_left.btn_delete]:
            btn.setFixedSize(110, 32)
            
        btn_row.addWidget(self.sidebar_left.btn_import)
        btn_row.addStretch(1)
        btn_row.addWidget(self.sidebar_left.btn_delete)
        lyt.addLayout(btn_row)
        return card

    def _make_output_panel(self) -> QFrame:
        card = _card()
        lyt = QVBoxLayout(card)
        lyt.setContentsMargins(14, 14, 14, 14)
        lyt.setSpacing(10)

        lbl = QLabel("FOLDER HASIL")
        lbl.setProperty("role", "sectionTitle")
        lyt.addWidget(lbl)

        _sp(self.sidebar_right.tree_view, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lyt.addWidget(self.sidebar_right.tree_view, stretch=1)

        btn_row = QHBoxLayout()
        self.sidebar_right.btn_back.setText("[BALIK]")
        self.sidebar_right.btn_explore.setText("[FOLDER]")
        
        for btn in [self.sidebar_right.btn_back, self.sidebar_right.btn_explore]:
            btn.setFixedSize(110, 32)
            
        btn_row.addWidget(self.sidebar_right.btn_back)
        btn_row.addStretch(1)
        btn_row.addWidget(self.sidebar_right.btn_explore)
        lyt.addLayout(btn_row)
        return card

    def _make_preview_col(self) -> QFrame:
        card = _card()
        card.setFixedWidth(320)
        
        lyt = QVBoxLayout(card)
        lyt.setContentsMargins(14, 14, 14, 14)
        lyt.setSpacing(10)

        lbl = QLabel("PREVIEW VIDEO")
        lbl.setProperty("role", "sectionTitle")
        lyt.addWidget(lbl)

        _sp(self.sidebar_right.video_widget, QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        lyt.addWidget(self.sidebar_right.video_widget, stretch=1)

        div = QFrame()
        div.setProperty("role", "divider")
        lyt.addWidget(div)

        nav_top_row = QHBoxLayout()
        nav_top_row.setSpacing(8)
        
        self.btn_mulai = QPushButton("[MULAI]")
        self.btn_mulai.setProperty("role", "accentBtn")
        self.btn_stop_preview = QPushButton("[BERENTI]")
        self.btn_stop_preview.setProperty("role", "dangerBtn")
        self.btn_next = QPushButton("[SELANJUTNYA]")
        
        self.btn_mulai.clicked.connect(self.sidebar_right._toggle_play)
        self.btn_stop_preview.clicked.connect(self.sidebar_right.player.stop)

        for btn in [self.btn_mulai, self.btn_stop_preview]:
            btn.setFixedHeight(34)
            nav_top_row.addWidget(btn)
            
        self.btn_next.setFixedHeight(34)

        lyt.addLayout(nav_top_row)
        lyt.addWidget(self.btn_next)
        return card

    def _wire_signals(self) -> None:
        self.sig_log.connect(self._on_log)
        self.sig_progress.connect(self._on_progress)
        self.sig_state.connect(self._on_state_changed)
        self.renderer.set_on_log(lambda m: self.sig_log.emit(m))
        self.renderer.set_on_progress(lambda *a: self.sig_progress.emit(*a))
        self.renderer.set_on_state_changed(lambda s: self.sig_state.emit(s))

    @Slot(str)
    def _on_log(self, msg: str) -> None:
        self.render_panel.write_log(msg)

    @Slot(int, int, float, float, float, float, float)
    def _on_progress(self, seg: int, total: int, sp: float, op: float, fps: float, spd: float, eta: float) -> None:
        self.render_panel.update_progress(seg, total, sp, op, fps, spd, eta)

    @Slot(object)
    def _on_state_changed(self, state: QueueState) -> None:
        self.render_panel.update_state(state)
        if state == QueueState.RUNNING:
            self.lbl_status.setText("LAGI PROSES")
            self.lbl_status.setProperty("role", "statusRunning")
        elif state == QueueState.PAUSED:
            self.lbl_status.setText("BENTAR")
            self.lbl_status.setProperty("role", "statusPaused")
        else:
            self.lbl_status.setText("SIAP")
            self.lbl_status.setProperty("role", "statusReady")
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    def _start_render(self) -> None:
        selected = self.sidebar_left.get_selected_paths()
        if selected:
            self.renderer.add_sources(selected)
            self.renderer.start()

    def _pause_render(self) -> None:
        self.renderer.pause()

    def _continue_render(self) -> None:
        self.renderer.resume()

    def _stop_render(self) -> None:
        self.renderer.stop()

    def _refresh_app(self) -> None:
        self.sidebar_left.refresh()
        self.renderer.initialise()
        self.render_panel.update_state(self.renderer.get_state())

    def _toggle_theme(self, checked: bool) -> None:
        self._dark_mode = checked
        apply_theme(self, dark=checked)
        self.btn_theme.setText("🌙 Gelap" if checked else "☀️ Terang")