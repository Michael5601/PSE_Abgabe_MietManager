from datetime import date as date_type

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from mietmanager.models import Mieteinheit, Mieter, Mietvertrag
from mietmanager.services import GeschaeftsregelFehler, pruefe_keine_ueberlappung, pruefe_vertragszeitraum


def _to_qdate(d: date_type) -> QDate:
    return QDate(d.year, d.month, d.day)


class MietvertragDialog(QDialog):
    def __init__(self, session: Session, parent=None, mietvertrag: Mietvertrag | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.mietvertrag = mietvertrag
        self.setWindowTitle("Mietvertrag bearbeiten" if mietvertrag else "Neuer Mietvertrag")

        self.mieteinheit_combo = QComboBox()
        for einheit in session.scalars(select(Mieteinheit)).all():
            self.mieteinheit_combo.addItem(
                f"{einheit.immobilie.bezeichnung} – {einheit.bezeichnung}", userData=einheit.id
            )

        self.mieter_combo = QComboBox()
        for mieter in session.scalars(select(Mieter)).all():
            self.mieter_combo.addItem(mieter.name, userData=mieter.id)

        heute = QDate.currentDate()
        self.beginn_edit = QDateEdit(_to_qdate(mietvertrag.beginn) if mietvertrag else heute)
        self.beginn_edit.setCalendarPopup(True)

        self.unbefristet_check = QCheckBox("läuft unbefristet")
        self.ende_edit = QDateEdit(_to_qdate(mietvertrag.ende) if (mietvertrag and mietvertrag.ende) else heute)
        self.ende_edit.setCalendarPopup(True)
        self.unbefristet_check.setChecked(not (mietvertrag and mietvertrag.ende))
        self.unbefristet_check.toggled.connect(self.ende_edit.setDisabled)
        self.ende_edit.setDisabled(self.unbefristet_check.isChecked())

        self.kaltmiete_spin = QDoubleSpinBox()
        self.kaltmiete_spin.setRange(0, 100_000)
        self.kaltmiete_spin.setSuffix(" €")
        self.kaltmiete_spin.setValue(float(mietvertrag.kaltmiete) if mietvertrag else 500.0)

        self.nk_spin = QDoubleSpinBox()
        self.nk_spin.setRange(0, 100_000)
        self.nk_spin.setSuffix(" €")
        self.nk_spin.setValue(float(mietvertrag.nebenkosten_vorauszahlung) if mietvertrag else 150.0)

        self.kaution_spin = QDoubleSpinBox()
        self.kaution_spin.setRange(0, 1_000_000)
        self.kaution_spin.setSuffix(" €")
        self.kaution_spin.setValue(float(mietvertrag.kaution) if mietvertrag else 1500.0)

        self.personen_spin = QSpinBox()
        self.personen_spin.setRange(1, 20)
        self.personen_spin.setValue(mietvertrag.personenzahl if mietvertrag else 1)

        if mietvertrag:
            index = self.mieteinheit_combo.findData(mietvertrag.mieteinheit_id)
            if index >= 0:
                self.mieteinheit_combo.setCurrentIndex(index)
            index = self.mieter_combo.findData(mietvertrag.mieter_id)
            if index >= 0:
                self.mieter_combo.setCurrentIndex(index)

        form = QFormLayout()
        form.addRow("Mieteinheit:", self.mieteinheit_combo)
        form.addRow("Mieter:", self.mieter_combo)
        form.addRow("Beginn:", self.beginn_edit)
        form.addRow("", self.unbefristet_check)
        form.addRow("Ende:", self.ende_edit)
        form.addRow("Kaltmiete:", self.kaltmiete_spin)
        form.addRow("NK-Vorauszahlung:", self.nk_spin)
        form.addRow("Kaution:", self.kaution_spin)
        form.addRow("Personenzahl:", self.personen_spin)

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
        mieteinheit_id = self.mieteinheit_combo.currentData()
        mieter_id = self.mieter_combo.currentData()
        if mieteinheit_id is None or mieter_id is None:
            QMessageBox.warning(self, "Eingabe unvollständig", "Bitte Mieteinheit und Mieter auswählen.")
            return

        beginn = self.beginn_edit.date().toPyDate()
        ende = None if self.unbefristet_check.isChecked() else self.ende_edit.date().toPyDate()

        bestehende = self.session.scalars(
            select(Mietvertrag).where(Mietvertrag.mieteinheit_id == mieteinheit_id)
        ).all()
        ausgenommen_id = self.mietvertrag.id if self.mietvertrag is not None else None

        try:
            pruefe_vertragszeitraum(beginn, ende)
            pruefe_keine_ueberlappung(bestehende, beginn, ende, ausgenommen_vertrag_id=ausgenommen_id)
        except GeschaeftsregelFehler as fehler:
            QMessageBox.warning(self, "Eingabe ungültig", str(fehler))
            return

        self.accept()

    def apply_to(self, mietvertrag: Mietvertrag) -> None:
        mietvertrag.mieteinheit_id = self.mieteinheit_combo.currentData()
        mietvertrag.mieter_id = self.mieter_combo.currentData()
        mietvertrag.beginn = self.beginn_edit.date().toPyDate()
        mietvertrag.ende = None if self.unbefristet_check.isChecked() else self.ende_edit.date().toPyDate()
        mietvertrag.kaltmiete = self.kaltmiete_spin.value()
        mietvertrag.nebenkosten_vorauszahlung = self.nk_spin.value()
        mietvertrag.kaution = self.kaution_spin.value()
        mietvertrag.personenzahl = self.personen_spin.value()
