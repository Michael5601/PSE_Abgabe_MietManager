from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from mietmanager.data import get_or_create_profil


class ProfilFormWidget(QWidget):
    """Formular zur Pflege der Vermieter-Stammdaten (Briefkopf-Absender der Abrechnung)."""

    gespeichert = pyqtSignal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.profil = get_or_create_profil(session)

        titel = QLabel("<b>Vermieter-Profil</b>")
        hinweis = QLabel(
            "Diese Angaben erscheinen als Absender/Briefkopf auf der Nebenkostenabrechnung."
        )
        hinweis.setWordWrap(True)

        self.name_edit = QLineEdit(self.profil.name)
        self.strasse_edit = QLineEdit(self.profil.strasse)
        self.plz_edit = QLineEdit(self.profil.plz)
        self.ort_edit = QLineEdit(self.profil.ort)
        self.telefon_edit = QLineEdit(self.profil.telefon or "")
        self.email_edit = QLineEdit(self.profil.email or "")
        self.iban_edit = QLineEdit(self.profil.iban or "")

        form = QFormLayout()
        form.addRow("Name / Firma:", self.name_edit)
        form.addRow("Straße:", self.strasse_edit)
        form.addRow("PLZ:", self.plz_edit)
        form.addRow("Ort:", self.ort_edit)
        form.addRow("Telefon:", self.telefon_edit)
        form.addRow("E-Mail:", self.email_edit)
        form.addRow("IBAN:", self.iban_edit)

        speichern_btn = QPushButton("💾 Speichern")
        speichern_btn.setObjectName("primaryButton")
        speichern_btn.clicked.connect(self._speichern)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(titel)
        layout.addWidget(hinweis)
        layout.addSpacing(8)
        layout.addLayout(form)
        layout.addWidget(speichern_btn)
        self.setLayout(layout)

    def _speichern(self) -> None:
        if not self.name_edit.text().strip() or not self.strasse_edit.text().strip():
            QMessageBox.warning(self, "Eingabe unvollständig", "Name und Straße sind Pflichtfelder.")
            return
        self.profil.name = self.name_edit.text().strip()
        self.profil.strasse = self.strasse_edit.text().strip()
        self.profil.plz = self.plz_edit.text().strip()
        self.profil.ort = self.ort_edit.text().strip()
        self.profil.telefon = self.telefon_edit.text().strip() or None
        self.profil.email = self.email_edit.text().strip() or None
        self.profil.iban = self.iban_edit.text().strip() or None
        self.session.commit()
        self.gespeichert.emit()
