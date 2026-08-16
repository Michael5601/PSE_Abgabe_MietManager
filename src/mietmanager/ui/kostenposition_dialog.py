from datetime import date as date_type

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from mietmanager.models import Immobilie, Kostenposition, Umlageschluessel

UMLAGE_LABELS = {
    Umlageschluessel.FLAECHE: "nach Fläche",
    Umlageschluessel.PERSONEN: "nach Personen",
    Umlageschluessel.EINHEITEN: "gleichmäßig je Einheit",
}


def _to_qdate(d: date_type) -> QDate:
    return QDate(d.year, d.month, d.day)


class KostenpositionDialog(QDialog):
    def __init__(self, session: Session, parent=None, kostenposition: Kostenposition | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.kostenposition = kostenposition
        self.setWindowTitle("Kostenposition bearbeiten" if kostenposition else "Neue Kostenposition")

        self.immobilie_combo = QComboBox()
        for immobilie in session.scalars(select(Immobilie)).all():
            self.immobilie_combo.addItem(immobilie.bezeichnung, userData=immobilie.id)
        if kostenposition:
            index = self.immobilie_combo.findData(kostenposition.immobilie_id)
            if index >= 0:
                self.immobilie_combo.setCurrentIndex(index)

        self.kostenart_edit = QLineEdit(kostenposition.kostenart if kostenposition else "")

        self.betrag_spin = QDoubleSpinBox()
        self.betrag_spin.setRange(0, 1_000_000)
        self.betrag_spin.setSuffix(" €")
        self.betrag_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.betrag_spin.setValue(float(kostenposition.betrag) if kostenposition else 100.0)

        heute = QDate.currentDate()
        self.start_edit = QDateEdit(
            _to_qdate(kostenposition.zeitraum_start) if kostenposition else QDate(heute.year(), 1, 1)
        )
        self.start_edit.setCalendarPopup(True)
        self.ende_edit = QDateEdit(
            _to_qdate(kostenposition.zeitraum_ende) if kostenposition else QDate(heute.year(), 12, 31)
        )
        self.ende_edit.setCalendarPopup(True)

        self.umlage_combo = QComboBox()
        for schluessel, label in UMLAGE_LABELS.items():
            self.umlage_combo.addItem(label, userData=schluessel)
        if kostenposition:
            index = self.umlage_combo.findData(kostenposition.umlageschluessel)
            if index >= 0:
                self.umlage_combo.setCurrentIndex(index)

        form = QFormLayout()
        form.addRow("Immobilie:", self.immobilie_combo)
        form.addRow("Kostenart:", self.kostenart_edit)
        form.addRow("Betrag:", self.betrag_spin)
        form.addRow("Zeitraum von:", self.start_edit)
        form.addRow("Zeitraum bis:", self.ende_edit)
        form.addRow("Umlageschlüssel:", self.umlage_combo)

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
        if not self.kostenart_edit.text().strip():
            QMessageBox.warning(self, "Eingabe unvollständig", "Kostenart ist ein Pflichtfeld.")
            return
        if self.immobilie_combo.currentData() is None:
            QMessageBox.warning(self, "Eingabe unvollständig", "Bitte eine Immobilie auswählen.")
            return
        if self.start_edit.date() >= self.ende_edit.date():
            QMessageBox.warning(self, "Ungültiger Zeitraum", "Das Startdatum muss vor dem Enddatum liegen.")
            return
        self.accept()

    def apply_to(self, kostenposition: Kostenposition) -> None:
        kostenposition.immobilie_id = self.immobilie_combo.currentData()
        kostenposition.kostenart = self.kostenart_edit.text().strip()
        kostenposition.betrag = self.betrag_spin.value()
        kostenposition.zeitraum_start = self.start_edit.date().toPyDate()
        kostenposition.zeitraum_ende = self.ende_edit.date().toPyDate()
        kostenposition.umlageschluessel = self.umlage_combo.currentData()
