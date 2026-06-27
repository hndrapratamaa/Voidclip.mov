from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from backend.config import APP_NAME, APP_VERSION
from backend.queue_manager import QueueState
from backend.renderer import Renderer
from backend.lang_id import (
    GITHUB_PROFILE, GITHUB_REPO, PAYPAL_DONATE,
    BTN_DONATE, BTN_GITHUB, BTN_BALIK, BTN_SEGERIN,
    LBL_INPUT, LBL_OUTPUT, LBL_LOG,
    MSG_IDLE, MSG_MULAI_PROSES, MSG_JEDA,
)
from frontend.about_dialog import AboutDialog
from frontend.render_panel import RenderPanel
from frontend.sidebar_left import SidebarLeft
from frontend.sidebar_right import SidebarRight
from frontend.theme import apply_theme
from frontend.widgets.icon_button import IconButton
from frontend.widgets.terminal_log import TerminalLog
from frontend.auto_up.controller import AutoUpController

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_ICON_SVG = _ASSETS / "icons" / "voidclip_icon.svg"
_ICON_48  = _ASSETS / "icons" / "voidclip_icon_48.png"


def _sp(w: QWidget, h_pol, v_pol) -> QWidget:
    w.setSizePolicy(h_pol, v_pol)
    return w


def _card(inset: bool = False) -> QFrame:
    f = QFrame()
    f.setProperty("role", "card-inset" if inset else "card")
    f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return f


class MainWindow(QMainWindow):
    sig_log      = Signal(str)
    sig_progress = Signal(int, int, float, float, float, float, float)
    sig_state    = Signal(object)

    def __init__(self, renderer: Renderer) -> None:
        super().__init__()
        self.renderer    = renderer
        self._dark_mode  = True
        self._about_dlg: AboutDialog | None = None

        self.setWindowTitle(f"VOIDCLIP.MOV v{APP_VERSION}")
        self.setMinimumSize(1100, 700)
        self.resize(1340, 860)

        icon_path = str(_ICON_48) if _ICON_48.exists() else str(_ICON_SVG)
        if Path(icon_path).exists():
            self.setWindowIcon(QIcon(icon_path))

        self.sidebar_left  = SidebarLeft(self.renderer)
        self.sidebar_right = SidebarRight()
        self.render_panel  = RenderPanel(self.renderer)

        self.terminal_log = TerminalLog()

        self.auto_ctrl = AutoUpController(
            main_window=self,
            log_cb=lambda m: self.sig_log.emit(m),
        )

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

        self.render_panel.btn_start.setText("▶  MULAI RENDER")
        self.render_panel.btn_pause.setText("⏸  BENTAR")
        self.render_panel.btn_continue.setText("▶  LANJUT")
        self.render_panel.btn_stop.setText("⏹  BERENTI")
        self.render_panel.btn_refresh.setText("↺  SEGERIN")

        self.render_panel.btn_start.clicked.connect(self._start_render)
        self.render_panel.btn_pause.clicked.connect(self._pause_render)
        self.render_panel.btn_continue.clicked.connect(self._continue_render)
        self.render_panel.btn_stop.clicked.connect(self._stop_render)
        self.render_panel.btn_refresh.clicked.connect(self._refresh_app)

    def _make_topbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setContentsMargins(4, 0, 4, 0)
        bar.setSpacing(6)

        logo_lbl = QLabel()
        if _ICON_48.exists():
            pix = QPixmap(str(_ICON_48)).scaled(
                28, 28,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(pix)
            logo_lbl.setFixedSize(32, 32)
            bar.addWidget(logo_lbl)

        lbl = QLabel("VOIDCLIP.MOV")
        lbl.setProperty("role", "appTitle")
        _sp(lbl, QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        bar.addWidget(lbl)

        bar.addStretch()

        self._btn_github_profile = IconButton(
            "⌥", tooltip="GitHub Profile gua blay", size=32,
            on_click=lambda: QDesktopServices.openUrl(QUrl(GITHUB_PROFILE)),
        )
        self._btn_github_repo = IconButton(
            "⌂", tooltip="Repo Voidclip di GitHub", size=32,
            on_click=lambda: QDesktopServices.openUrl(QUrl(GITHUB_REPO)),
        )
        self._btn_donate = IconButton(
            "♥", tooltip="Traktir bos via PayPal", size=32,
            on_click=lambda: QDesktopServices.openUrl(QUrl(PAYPAL_DONATE)),
        )
        self._btn_about = IconButton(
            "!", tooltip="Info aplikasi", size=32,
            on_click=self._show_about,
        )
        self._btn_copy_log = IconButton(
            "⎘", tooltip="Salin semua log", size=32,
            on_click=self._copy_log,
        )
        self._btn_clear_log = IconButton(
            "✕", tooltip="Bersihin log terminal", size=32,
            on_click=self._clear_log,
        )
        self.btn_theme = IconButton(
            "🌙", tooltip="Ganti mode gelap/terang", size=32,
        )
        self.btn_theme.setCheckable(True)
        self.btn_theme.setChecked(True)
        self.btn_theme.clicked.connect(self._toggle_theme)

        for btn in [
            self._btn_github_profile,
            self._btn_github_repo,
            self._btn_donate,
            self._btn_about,
            self._btn_copy_log,
            self._btn_clear_log,
            self.btn_theme,
        ]:
            bar.addWidget(btn)

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

        self.btn_auto_up = QPushButton("⬆  AUTO UP")
        self.btn_auto_up.setProperty("role", "accentBtn")
        self.btn_auto_up.clicked.connect(self._launch_auto_up)

        control_buttons = [
            self.render_panel.btn_start,
            self.render_panel.btn_pause,
            self.render_panel.btn_continue,
            self.render_panel.btn_stop,
            self.render_panel.btn_refresh,
            self.btn_auto_up,
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
        lyt.setSpacing(8)

        hdr = QHBoxLayout()
        lbl = QLabel("LOG TERMINAL")
        lbl.setProperty("role", "sectionTitle")
        hdr.addWidget(lbl)
        hdr.addStretch()
        lyt.addLayout(hdr)

        _sp(self.terminal_log, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lyt.addWidget(self.terminal_log, stretch=1)
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
        self.sidebar_left.btn_import.setText("⬇  IMPORT")
        self.sidebar_left.btn_delete.setText("🗑  APUS")
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
        self.sidebar_right.btn_back.setText("◀  BALIK")
        self.sidebar_right.btn_explore.setText("📁  FOLDER")

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

        _sp(
            self.sidebar_right.video_widget,
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        lyt.addWidget(self.sidebar_right.video_widget, stretch=1)

        div = QFrame()
        div.setProperty("role", "divider")
        lyt.addWidget(div)

        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self.btn_play_preview = QPushButton("▶  PUTAR")
        self.btn_play_preview.setProperty("role", "accentBtn")
        self.btn_stop_preview = QPushButton("⏹  BERENTI")
        self.btn_stop_preview.setProperty("role", "dangerBtn")

        self.btn_play_preview.clicked.connect(self.sidebar_right._toggle_play)
        self.btn_stop_preview.clicked.connect(self.sidebar_right.player.stop)

        for btn in [self.btn_play_preview, self.btn_stop_preview]:
            btn.setFixedHeight(34)
            nav_row.addWidget(btn)

        lyt.addLayout(nav_row)

        self.btn_next = QPushButton("⏭  NEXT")
        self.btn_next.setFixedHeight(34)
        self.btn_next.clicked.connect(self._preview_next)
        lyt.addWidget(self.btn_next)

        self._btn_set_folder = QPushButton("📂  SET FOLDER EPISODE")
        self._btn_set_folder.setFixedHeight(30)
        self._btn_set_folder.clicked.connect(self._pick_episode_folder)
        lyt.addWidget(self._btn_set_folder)

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
        self.terminal_log.write_log(msg)

    @Slot(int, int, float, float, float, float, float)
    def _on_progress(
        self,
        seg: int, total: int,
        sp: float, op: float,
        fps: float, spd: float, eta: float,
    ) -> None:
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
        self.btn_theme.setText("🌙" if checked else "☀️")

    def _show_about(self) -> None:
        if self._about_dlg is None:
            self._about_dlg = AboutDialog(self)
        self._about_dlg.exec()

    def _copy_log(self) -> None:
        QApplication.clipboard().setText(self.terminal_log.toPlainText())
        self.terminal_log.write_log("Log disalin ke clipboard blay!")

    def _clear_log(self) -> None:
        self.terminal_log.clear_terminal()

    def _launch_auto_up(self) -> None:
        self.auto_ctrl.launch()

    def _pick_episode_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pilih Folder Episode blay",
            str(Path.home()),
        )
        if folder:
            self.auto_ctrl.set_episode_folder(Path(folder))
            self.terminal_log.write_log(f"Folder episode diset: {folder}")

    def _preview_next(self) -> None:
        from PySide6.QtCore import QUrl as _QUrl
        model     = self.sidebar_right.model
        cur_root  = self.sidebar_right.tree_view.rootIndex()
        cur_idx   = self.sidebar_right.tree_view.currentIndex()

        if not cur_idx.isValid():
            first = model.index(0, 0, cur_root)
            if first.isValid():
                self.sidebar_right.tree_view.setCurrentIndex(first)
                self.sidebar_right._on_double_click(first)
            return

        sib = cur_idx.sibling(cur_idx.row() + 1, 0)
        if not sib.isValid():
            sib = model.index(0, 0, cur_root)

        if sib.isValid():
            self.sidebar_right.tree_view.setCurrentIndex(sib)
            self.sidebar_right._on_double_click(sib)

    def closeEvent(self, event) -> None:
        self.auto_ctrl.close()
        super().closeEvent(event)
