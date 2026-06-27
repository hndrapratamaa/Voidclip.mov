from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from backend.lang_id import (
    MSG_IDLE,
)


class NeuButton(QPushButton):
    def __init__(self, label: str, role: str = "", parent=None) -> None:
        super().__init__(label, parent)
        if role:
            self.setProperty("role", role)
        self._depressed = False

    def press_down(self) -> None:
        if not self._depressed:
            self._depressed = True
            self.setProperty("depressed", "true")
            self._refresh_style()

    def pop_up(self) -> None:
        if self._depressed:
            self._depressed = False
            self.setProperty("depressed", "false")
            self._refresh_style()

    def _refresh_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)


class RenderPanel(QWidget):
    def __init__(self, renderer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.renderer = renderer
        self._build_ui()

    def _build_ui(self) -> None:
        self.stats_grid = QHBoxLayout()
        self.stats_grid.setSpacing(8)

        self._seg_label   = self._stat_box("SEGMENT", "0 / 0")
        self._fps_label   = self._stat_box("FPS", "0.0")
        self._speed_label = self._stat_box("SPEED", "0.00×")
        self._eta_label   = self._stat_box("ETA", "0m 0s")

        for box in [
            self._seg_label,
            self._fps_label,
            self._speed_label,
            self._eta_label,
        ]:
            self.stats_grid.addWidget(box)

        self.pb_segment = QProgressBar()
        self.pb_segment.setFormat("Part: %p%")
        self.pb_segment.setFixedHeight(12)

        self.pb_overall = QProgressBar()
        self.pb_overall.setObjectName("overallBar")
        self.pb_overall.setFormat("Overall: %p%")
        self.pb_overall.setFixedHeight(12)

        self.btn_start    = NeuButton("▶  MULAI RENDER", role="accentBtn")
        self.btn_pause    = NeuButton("⏸  BENTAR")
        self.btn_continue = NeuButton("▶  LANJUT")
        self.btn_stop     = NeuButton("⏹  BERENTI",     role="dangerBtn")
        self.btn_refresh  = NeuButton("↺  SEGERIN")

    def _stat_box(self, title: str, val: str) -> QWidget:
        box = QWidget()
        box.setProperty("role", "card-inset")
        lyt = QVBoxLayout(box)
        lyt.setContentsMargins(8, 6, 8, 6)
        lyt.setSpacing(2)

        t = QLabel(title)
        t.setProperty("role", "sectionTitle")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v = QLabel(val)
        v.setStyleSheet(
            "font-size: 14px; color: #0a84ff; font-weight: 700; background: transparent;"
        )
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box._val_lbl = v
        lyt.addWidget(t)
        lyt.addWidget(v)
        return box

    def _on_start_clicked(self) -> None:
        self.btn_start.press_down()

    def _on_pause_clicked(self) -> None:
        self.btn_pause.press_down()

    def _on_stop_clicked(self) -> None:
        self.btn_start.pop_up()
        self.btn_pause.pop_up()
        self.btn_continue.pop_up()

    def _on_continue_clicked(self) -> None:
        self.btn_continue.press_down()

    def write_log(self, msg: str) -> None:
        pass

    def update_progress(
        self,
        seg_num: int, total: int,
        seg_pct: float, overall_pct: float,
        fps: float, speed: float, eta: float,
    ) -> None:
        self._seg_label._val_lbl.setText(f"{seg_num} / {total}")
        self._fps_label._val_lbl.setText(f"{fps:.1f}")
        self._speed_label._val_lbl.setText(f"{speed:.2f}×")
        m, s = divmod(int(eta), 60)
        self._eta_label._val_lbl.setText(f"{m}m {s}s")
        self.pb_segment.setValue(int(seg_pct))
        self.pb_overall.setValue(int(overall_pct))

    def update_state(self, state) -> None:
        from backend.queue_manager import QueueState
        idle   = state == QueueState.IDLE
        running = state == QueueState.RUNNING
        paused  = state == QueueState.PAUSED
        busy    = state in (
            QueueState.RUNNING,
            QueueState.PAUSED,
            QueueState.QUEUEING,
        )

        self.btn_start.setEnabled(idle)
        self.btn_pause.setEnabled(running)
        self.btn_continue.setEnabled(paused)
        self.btn_stop.setEnabled(busy)
        self.btn_refresh.setEnabled(idle)

        if idle:
            self.btn_start.pop_up()
            self.btn_pause.pop_up()
            self.btn_continue.pop_up()
