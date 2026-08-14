from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from mietmanager.models import Anrede, Mieter

ANREDE_LABELS = {
    Anrede.HERR: "Herr",
    Anrede.FRAU: "Frau",
    Anrede.KEINE_ANGABE: "Keine Angabe",
}


class MieterDialog(QDialog):
    def __init__(self, parent=None, mieter: Mieter | None = None) -> None:
        super().__init__(parent)
        self.mieter = mieter
        self.setWindowTitle("Mieter bearbeiten" if mieter else "Neuer Mieter")

        self.anrede_combo = QComboBox()
        for anrede, label in ANREDE_LABELS.items():
            self.anrede_combo.addItem(label, userData=anrede)
        if mieter:
            index = self.anrede_combo.findData(mieter.anrede)
            if index >= 0:
                self.anrede_combo.setCurrentIndex(index)

        self.vorname_edit = QLineEdit(mieter.vorname if mieter else "")
        self.nachname_edit = QLineEdit(mieter.nachname if mieter else "")
        self.email_edit = QLineEdit((mieter.email or "") if mieter else "")
        self.telefon_edit = QLineEdit((mieter.telefon or "") if mieter else "")

        form = QFormLayout()
        form.addRow("Anrede:", self.anrede_combo)
        form.addRow("Vorname:", self.vorname_edit)
        form.addRow("Nachname:", self.nachname_edit)
        form.addRow("E-Mail:", self.email_edit)
        form.addRow("Telefon:", self.telefon_edit)

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
        if not self.vorname_edit.text().strip() or not self.nachname_edit.text().strip():
            QMessageBox.warning(self, "Eingabe unvollständig", "Vor- und Nachname sind Pflichtfelder.")
            return
        self.accept()

    def apply_to(self, mieter: Mieter) -> None:
        mieter.anrede = self.anrede_combo.currentData()
        mieter.vorname = self.vorname_edit.text().strip()
        mieter.nachname = self.nachname_edit.text().strip()
        mieter.email = self.email_edit.text().strip() or None
        mieter.telefon = self.telefon_edit.text().strip() or None
