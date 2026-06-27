from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

from backend.config import APP_NAME, APP_VERSION
from backend.lang_id import (
    GITHUB_REPO, PAYPAL_DONATE,
    BTN_DONATE, BTN_GITHUB,
)


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Tentang {APP_NAME}")
        self.setModal(True)
        self.setFixedSize(400, 420)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QWidget()
        card.setObjectName("AboutCard")
        card_lyt = QVBoxLayout(card)
        card_lyt.setContentsMargins(32, 28, 32, 24)
        card_lyt.setSpacing(0)

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setObjectName("BtnClose")
        btn_close.setFixedSize(22, 22)
        btn_close.clicked.connect(self.reject)
        close_row.addWidget(btn_close)
        card_lyt.addLayout(close_row)

        badge = QLabel("!")
        badge.setObjectName("AboutBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(56, 56)
        card_lyt.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)

        card_lyt.addSpacing(14)

        lbl_name = QLabel(APP_NAME)
        lbl_name.setObjectName("AboutAppName")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lyt.addWidget(lbl_name)

        lbl_ver = QLabel(f"versi {APP_VERSION}")
        lbl_ver.setObjectName("AboutVersion")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lyt.addWidget(lbl_ver)

        card_lyt.addSpacing(20)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setObjectName("AboutDivider")
        card_lyt.addWidget(divider)

        card_lyt.addSpacing(18)

        lbl_by = QLabel("dibuat dengan ❤️ oleh")
        lbl_by.setObjectName("AboutBy")
        lbl_by.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lyt.addWidget(lbl_by)

        lbl_dev = QLabel("hndrapratamaaa")
        lbl_dev.setObjectName("AboutDev")
        lbl_dev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lyt.addWidget(lbl_dev)

        card_lyt.addSpacing(6)

        lbl_desc = QLabel(
            "Video converter & auto-uploader buat konten kreator\n"
            "yang males ribet tapi tetep mau hasil kece, blay!"
        )
        lbl_desc.setObjectName("AboutDesc")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        card_lyt.addWidget(lbl_desc)

        card_lyt.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_github = QPushButton(f"  {BTN_GITHUB}")
        btn_github.setObjectName("BtnGithub")
        btn_github.setFixedHeight(36)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_REPO)))

        btn_donate = QPushButton(f"  {BTN_DONATE}")
        btn_donate.setObjectName("BtnDonate")
        btn_donate.setFixedHeight(36)
        btn_donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(PAYPAL_DONATE)))

        btn_row.addWidget(btn_github)
        btn_row.addWidget(btn_donate)
        card_lyt.addLayout(btn_row)

        card_lyt.addSpacing(10)

        lbl_license = QLabel("MIT License · Open Source · Gratis pakai blay")
        lbl_license.setObjectName("AboutLicense")
        lbl_license.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lyt.addWidget(lbl_license)

        root.addWidget(card)

    def _apply_style(self) -> None:
        # Same liquid-glass approach as theme.py: translucent flat fill +
        # bright specular edge top/left, faint dark edge bottom/right.
        self.setStyleSheet("""
            #AboutCard {
                background-color: rgba(255, 255, 255, 14);
                border-top: 1.5px solid rgba(255, 255, 255, 110);
                border-left: 1.5px solid rgba(255, 255, 255, 40);
                border-bottom: 1.5px solid rgba(0, 0, 0, 90);
                border-right: 1.5px solid rgba(0, 0, 0, 90);
                border-radius: 24px;
            }
            #BtnClose {
                background-color: rgba(255, 255, 255, 14);
                color: #aab3c2;
                border-top: 1.5px solid rgba(255, 255, 255, 90);
                border-left: 1.5px solid rgba(255, 255, 255, 40);
                border-bottom: 1.5px solid rgba(0, 0, 0, 90);
                border-right: 1.5px solid rgba(0, 0, 0, 90);
                border-radius: 11px;
                font-size: 10px;
                font-weight: 700;
                padding: 0;
            }
            #BtnClose:hover {
                border-top: 1.5px solid #ff453a;
                border-left: 1.5px solid #ff453a;
                color: #ff6860;
            }
            #AboutBadge {
                background-color: rgba(255, 255, 255, 14);
                color: #0a84ff;
                border-top: 1.5px solid rgba(255, 255, 255, 90);
                border-left: 1.5px solid rgba(255, 255, 255, 40);
                border-bottom: 1.5px solid rgba(0, 0, 0, 90);
                border-right: 1.5px solid rgba(0, 0, 0, 90);
                border-radius: 28px;
                font-size: 24px;
                font-weight: 900;
            }
            #AboutAppName {
                font-size: 20px;
                font-weight: 700;
                color: #F2F5F9;
                letter-spacing: -0.4px;
            }
            #AboutVersion {
                font-size: 11px;
                color: #717a89;
                font-weight: 500;
            }
            #AboutDivider {
                border: none;
                border-top: 1px solid rgba(255, 255, 255, 18);
                max-height: 1px;
                background: transparent;
            }
            #AboutBy {
                font-size: 11px;
                color: #717a89;
            }
            #AboutDev {
                font-size: 16px;
                font-weight: 700;
                color: #0a84ff;
                letter-spacing: 0.2px;
            }
            #AboutDesc {
                font-size: 11px;
                color: #aab3c2;
            }
            #BtnGithub {
                background-color: rgba(255, 255, 255, 14);
                color: #F2F5F9;
                border-top: 1.5px solid rgba(255, 255, 255, 90);
                border-left: 1.5px solid rgba(255, 255, 255, 40);
                border-bottom: 1.5px solid rgba(0, 0, 0, 90);
                border-right: 1.5px solid rgba(0, 0, 0, 90);
                border-radius: 14px;
                font-weight: 600;
                font-size: 11px;
            }
            #BtnGithub:hover {
                border-top: 1.5px solid #0a84ff;
                border-left: 1.5px solid #0a84ff;
                color: #3d9eff;
            }
            #BtnDonate {
                background-color: #0a84ff;
                color: #ffffff;
                border-top: 1.5px solid rgba(255, 255, 255, 110);
                border-left: 1.5px solid rgba(255, 255, 255, 60);
                border-bottom: 1.5px solid #0060cc;
                border-right: 1.5px solid #0060cc;
                border-radius: 14px;
                font-weight: 700;
                font-size: 11px;
            }
            #BtnDonate:hover {
                background-color: #3d9eff;
                border-top: 1.5px solid rgba(255, 255, 255, 140);
                border-left: 1.5px solid rgba(255, 255, 255, 90);
            }
            #AboutLicense {
                font-size: 10px;
                color: #717a89;
            }
        """)