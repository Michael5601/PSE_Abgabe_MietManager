from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from mietmanager.models import Mieteinheit


class MieteinheitDialog(QDialog):
    def __init__(self, parent=None, mieteinheit: Mieteinheit | None = None) -> None:
        super().__init__(parent)
        self.mieteinheit = mieteinheit
        self.setWindowTitle("Mieteinheit bearbeiten" if mieteinheit else "Neue Mieteinheit")

        self.bezeichnung_edit = QLineEdit(mieteinheit.bezeichnung if mieteinheit else "")

        self.flaeche_spin = QDoubleSpinBox()
        self.flaeche_spin.setRange(1, 9999)
        self.flaeche_spin.setSuffix(" qm")
        self.flaeche_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.flaeche_spin.setValue(float(mieteinheit.flaeche_qm) if mieteinheit else 50.0)

        self.zimmer_spin = QDoubleSpinBox()
        self.zimmer_spin.setRange(0.5, 20)
        self.zimmer_spin.setSingleStep(0.5)
        self.zimmer_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.zimmer_spin.setValue(float(mieteinheit.zimmeranzahl) if mieteinheit else 2.0)

        form = QFormLayout()
        form.addRow("Bezeichnung:", self.bezeichnung_edit)
        form.addRow("Fläche:", self.flaeche_spin)
        form.addRow("Zimmer:", self.zimmer_spin)

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
        if not self.bezeichnung_edit.text().strip():
            QMessageBox.warning(self, "Eingabe unvollständig", "Bezeichnung ist ein Pflichtfeld.")
            return
        self.accept()

    def apply_to(self, mieteinheit: Mieteinheit) -> None:
        mieteinheit.bezeichnung = self.bezeichnung_edit.text().strip()
        mieteinheit.flaeche_qm = self.flaeche_spin.value()
        mieteinheit.zimmeranzahl = self.zimmer_spin.value()
