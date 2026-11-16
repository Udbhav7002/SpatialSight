"""
Connect Phone Modal - Sleek Dialog for Device Connection & Troubleshooting.

Presented when START is clicked and phone camera is not detected.
Features:
- Matching Forest Green & Brass Gold styling (#15370D, #E5CD82, #FFF2B4)
- Step-by-step instructions
- Retry, Developer Fallback (Webcam), and Cancel buttons
- Zero emojis
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt

from ui.theme import BG, SURFACE, BORDER, TEXT, TEXT_MUTED, BORDER_MUTED


class ConnectPhoneDialog(QDialog):
    """Modal popup prompting user to connect phone camera."""

    RESULT_CANCEL = 0
    RESULT_RETRY = 1
    RESULT_USE_WEBCAM = 2

    def __init__(self, parent=None, diagnostic_msg: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Spatial Sight")
        self.setModal(True)
        self.setFixedSize(480, 360)
        self.action_result = self.RESULT_CANCEL

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG};
                border: 2px solid {BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Connect your phone camera")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            color: {TEXT};
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """)
        layout.addWidget(title)

        # Instruction card
        card = QFrame()
        card.setStyleSheet(f"""
            background-color: {SURFACE};
            border: 1px solid {BORDER_MUTED};
            border-radius: 8px;
            padding: 12px;
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        instructions = [
            "1. Connect Android phone to computer via USB-C cable.",
            "2. Turn on Developer Options & USB Debugging on phone.",
            "3. Tap 'Allow USB debugging' when prompted on screen.",
            "4. SpatialSight app will auto-launch and stream to PC.",
        ]
        for step in instructions:
            lbl = QLabel(step)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; line-height: 1.4;")
            card_layout.addWidget(lbl)

        if diagnostic_msg:
            diag_lbl = QLabel(f"Status: {diagnostic_msg}")
            diag_lbl.setWordWrap(True)
            diag_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px; font-weight: 600; margin-top: 4px;")
            card_layout.addWidget(diag_lbl)

        layout.addWidget(card)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_retry = QPushButton("Retry")
        btn_retry.setFixedHeight(38)
        btn_retry.clicked.connect(self._on_retry)

        btn_webcam = QPushButton("Dev: Use Webcam")
        btn_webcam.setFixedHeight(38)
        btn_webcam.clicked.connect(self._on_webcam)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(38)
        btn_cancel.clicked.connect(self._on_cancel)

        btn_row.addWidget(btn_retry)
        btn_row.addWidget(btn_webcam)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _on_retry(self):
        self.action_result = self.RESULT_RETRY
        self.accept()

    def _on_webcam(self):
        self.action_result = self.RESULT_USE_WEBCAM
        self.accept()

    def _on_cancel(self):
        self.action_result = self.RESULT_CANCEL
        self.reject()
