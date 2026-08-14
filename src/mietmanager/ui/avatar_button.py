from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget
from sqlalchemy.orm import Session

from mietmanager.data import get_or_create_profil
from mietmanager.ui.profil_widget import ProfilFormWidget

POPUP_WIDTH = 340


def _initialen(name: str) -> str:
    teile = [t for t in name.split() if t]
    if not teile:
        return "?"
    if len(teile) == 1:
        return teile[0][0].upper()
    return (teile[0][0] + teile[-1][0]).upper()


class _ProfilPopup(QWidget):
    """Frei schwebendes Popup-Panel mit dem Vermieter-Profil, schließt sich bei Klick daneben."""

    def __init__(self, session: Session, on_gespeichert) -> None:
        super().__init__(None, Qt.WindowType.Popup)
        self.setObjectName("profilPopupWindow")
        self.setFixedWidth(POPUP_WIDTH)

        self.form = ProfilFormWidget(session)
        self.form.gespeichert.connect(on_gespeichert)
        self.form.gespeichert.connect(self.close)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.form)
        self.setLayout(layout)


class ProfilAvatarButton(QPushButton):
    """Kreisförmiger Profil-Button, öffnet das Vermieter-Profil als Popup."""

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.setObjectName("avatarButton")
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Vermieter-Profil")
        self._popup: _ProfilPopup | None = None
        self.clicked.connect(self._oeffne_popup)
        self._aktualisiere_initialen()

    def _aktualisiere_initialen(self) -> None:
        profil = get_or_create_profil(self.session)
        self.setText(_initialen(profil.name))

    def _oeffne_popup(self) -> None:
        # Referenz auf self merken. Ohne würde Python das Popup sofort wieder
        # einsammeln, da keine andere Variable mehr darauf zeigt.
        self._popup = _ProfilPopup(self.session, self._aktualisiere_initialen)
        self._popup.adjustSize()
        ziel = self.mapToGlobal(QPoint(self.width() - self._popup.width(), self.height() + 8))
        self._popup.move(ziel)
        self._popup.show()
        self._popup.raise_()
        self._popup.activateWindow()
