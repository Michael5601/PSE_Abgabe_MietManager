from datetime import date

from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from mietmanager.models import Immobilie


class ImmobilieDialog(QDialog):
    def __init__(self, parent=None, immobilie: Immobilie | None = None) -> None:
        super().__init__(parent)
        self.immobilie = immobilie
        self.setWindowTitle("Immobilie bearbeiten" if immobilie else "Neue Immobilie")

        self.bezeichnung_edit = QLineEdit(immobilie.bezeichnung if immobilie else "")
        self.strasse_edit = QLineEdit(immobilie.strasse if immobilie else "")
        self.plz_edit = QLineEdit(immobilie.plz if immobilie else "")
        self.ort_edit = QLineEdit(immobilie.ort if immobilie else "")
        self.baujahr_spin = QSpinBox()
        self.baujahr_spin.setRange(0, 2100)
        self.baujahr_spin.setSpecialValueText("unbekannt")
        self.baujahr_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        if immobilie is not None:
            # Beim Bearbeiten den tatsächlich gespeicherten Wert zeigen (ggf. "unbekannt").
            self.baujahr_spin.setValue(immobilie.baujahr or 0)
        else:
            # Beim Neuanlegen mit dem aktuellen Jahr statt 0 starten, da sonst jeder Klick auf die
            # Pfeil-Buttons das Baujahr nur um 1 verändert und man von "unbekannt" aus Hunderte Klicks
            # bräuchte, um ein realistisches Baujahr zu erreichen.
            self.baujahr_spin.setValue(date.today().year)

        form = QFormLayout()
        form.addRow("Bezeichnung:", self.bezeichnung_edit)
        form.addRow("Straße:", self.strasse_edit)
        form.addRow("PLZ:", self.plz_edit)
        form.addRow("Ort:", self.ort_edit)
        form.addRow("Baujahr:", self.baujahr_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _validate_and_accept(self) -> None:
        if not self.bezeichnung_edit.text().strip() or not self.strasse_edit.text().strip():
            QMessageBox.warning(self, "Eingabe unvollständig", "Bezeichnung und Straße sind Pflichtfelder.")
            return
        self.accept()

    def apply_to(self, immobilie: Immobilie) -> None:
        immobilie.bezeichnung = self.bezeichnung_edit.text().strip()
        immobilie.strasse = self.strasse_edit.text().strip()
        immobilie.plz = self.plz_edit.text().strip()
        immobilie.ort = self.ort_edit.text().strip()
        immobilie.baujahr = self.baujahr_spin.value() or None
