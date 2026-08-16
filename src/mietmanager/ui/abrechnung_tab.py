import os
from pathlib import Path

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from mietmanager.data import get_or_create_profil
from mietmanager.models import Immobilie, Nebenkostenabrechnung
from mietmanager.services import (
    AbrechnungsFehler,
    GeschaeftsregelFehler,
    erstelle_abrechnung,
    exportiere_abrechnung,
    pruefe_profil_vollstaendig,
)

RESULT_COLUMNS = ["Mieter", "Kostenanteil", "Vorauszahlung", "Saldo"]


class AbrechnungTab(QWidget):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.aktuelle_abrechnung: Nebenkostenabrechnung | None = None

        self.immobilie_combo = QComboBox()
        self._lade_immobilien()

        today = QDate.currentDate()
        self.start_edit = QDateEdit(QDate(today.year(), 1, 1))
        self.start_edit.setCalendarPopup(True)
        self.ende_edit = QDateEdit(QDate(today.year(), 12, 31))
        self.ende_edit.setCalendarPopup(True)

        erstellen_btn = QPushButton("▶ Abrechnung erstellen")
        erstellen_btn.setObjectName("primaryButton")
        erstellen_btn.clicked.connect(self.erstelle_abrechnung)

        self.export_btn = QPushButton("📄 Als PDF exportieren…")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._exportiere_pdf)

        form = QFormLayout()
        form.addRow("Immobilie:", self.immobilie_combo)
        form.addRow("Zeitraum von:", self.start_edit)
        form.addRow("Zeitraum bis:", self.ende_edit)

        self.status_label = QLabel()

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(len(RESULT_COLUMNS))
        self.result_table.setHorizontalHeaderLabels(RESULT_COLUMNS)
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        btn_row = QHBoxLayout()
        btn_row.addWidget(erstellen_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btn_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_table)
        self.setLayout(layout)

    def _lade_immobilien(self) -> None:
        self.immobilie_combo.clear()
        for immobilie in self.session.scalars(select(Immobilie)).all():
            self.immobilie_combo.addItem(immobilie.bezeichnung, userData=immobilie.id)

    def refresh(self) -> None:
        """Lädt die Immobilien-Auswahl neu, z.B. wenn in einem anderen Tab eine Immobilie angelegt
        wurde. Ein bereits berechnetes Abrechnungsergebnis bleibt dabei bewusst erhalten."""
        self._lade_immobilien()

    def erstelle_abrechnung(self) -> None:
        immobilie_id = self.immobilie_combo.currentData()
        if immobilie_id is None:
            return
        immobilie = self.session.get(Immobilie, immobilie_id)
        start = self.start_edit.date().toPyDate()
        ende = self.ende_edit.date().toPyDate()

        try:
            abrechnung = erstelle_abrechnung(self.session, immobilie, start, ende)
        except AbrechnungsFehler as exc:
            QMessageBox.warning(self, "Abrechnung nicht möglich", str(exc))
            return

        self.aktuelle_abrechnung = abrechnung
        self.export_btn.setEnabled(True)

        self.status_label.setText(
            f"Abrechnung für {immobilie.bezeichnung} ({start} – {ende}) erstellt."
        )
        self.result_table.setRowCount(len(abrechnung.positionen))
        for row, position in enumerate(abrechnung.positionen):
            values = [
                position.mietvertrag.mieter.name,
                f"{float(position.anteil_kosten):,.2f} €",
                f"{float(position.geleistete_vorauszahlung):,.2f} €",
                f"{float(position.saldo):,.2f} €",
            ]
            for col, value in enumerate(values):
                self.result_table.setItem(row, col, QTableWidgetItem(value))
        self.result_table.resizeColumnsToContents()

    def _exportiere_pdf(self) -> None:
        if self.aktuelle_abrechnung is None:
            return

        profil = get_or_create_profil(self.session)
        try:
            pruefe_profil_vollstaendig(profil)
        except GeschaeftsregelFehler as fehler:
            QMessageBox.warning(self, "Vermieter-Profil unvollständig", str(fehler))
            return

        ordner = QFileDialog.getExistingDirectory(self, "Zielordner für PDF-Export wählen")
        if not ordner:
            return

        try:
            dateien = exportiere_abrechnung(self.aktuelle_abrechnung, profil, Path(ordner))
        except GeschaeftsregelFehler as fehler:
            QMessageBox.warning(self, "Vermieter-Profil unvollständig", str(fehler))
            return
        QMessageBox.information(
            self,
            "Export abgeschlossen",
            f"{len(dateien)} PDF-Datei(en) wurden erstellt:\n" + "\n".join(p.name for p in dateien),
        )
        os.startfile(ordner)  # noqa: S606 (bewusstes Öffnen des vom Nutzer gewählten Zielordners)
