from pathlib import Path

from PyQt6.QtWidgets import QApplication

_STYLE_PATH = Path(__file__).parent / "resources" / "style.qss"


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(_STYLE_PATH.read_text(encoding="utf-8"))
