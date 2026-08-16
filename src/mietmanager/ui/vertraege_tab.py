from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from mietmanager.models import Mietvertrag
from mietmanager.services import GeschaeftsregelFehler, pruefe_mietvertrag_loeschbar
from mietmanager.ui.mietvertrag_dialog import MietvertragDialog

COLUMNS = [
    "Mieter",
    "Immobilie",
    "Mieteinheit",
    "Beginn",
    "Ende",
    "Kaltmiete",
    "NK-Vorauszahlung",
    "Kaution",
    "Personen",
]


class VertraegeTab(QWidget):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self._vertraege: list[Mietvertrag] = []

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self._bearbeiten)

        neu_btn = QPushButton("＋ Neu…")
        neu_btn.setObjectName("primaryButton")
        neu_btn.clicked.connect(self._neu)
        bearbeiten_btn = QPushButton("✎ Bearbeiten…")
        bearbeiten_btn.clicked.connect(self._bearbeiten)
        loeschen_btn = QPushButton("🗑 Löschen")
        loeschen_btn.setObjectName("dangerButton")
        loeschen_btn.clicked.connect(self._loeschen)
        refresh_btn = QPushButton("⟳ Aktualisieren")
        refresh_btn.clicked.connect(self.refresh)

        btn_row = QHBoxLayout()
        btn_row.addWidget(neu_btn)
        btn_row.addWidget(bearbeiten_btn)
        btn_row.addWidget(loeschen_btn)
        btn_row.addStretch()
        btn_row.addWidget(refresh_btn)

        layout = QVBoxLayout()
        layout.addLayout(btn_row)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh()

    def refresh(self) -> None:
        self._vertraege = list(self.session.scalars(select(Mietvertrag)).all())
        self.table.setRowCount(len(self._vertraege))
        for row, vertrag in enumerate(self._vertraege):
            values = [
                vertrag.mieter.name,
                vertrag.mieteinheit.immobilie.bezeichnung,
                vertrag.mieteinheit.bezeichnung,
                vertrag.beginn.isoformat(),
                vertrag.ende.isoformat() if vertrag.ende else "laufend",
                f"{float(vertrag.kaltmiete):,.2f} €",
                f"{float(vertrag.nebenkosten_vorauszahlung):,.2f} €",
                f"{float(vertrag.kaution):,.2f} €",
                str(vertrag.personenzahl),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def _selected(self) -> Mietvertrag | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._vertraege):
            return None
        return self._vertraege[row]

    def _neu(self) -> None:
        dialog = MietvertragDialog(self.session, self)
        if dialog.exec():
            vertrag = Mietvertrag()
            dialog.apply_to(vertrag)
            self.session.add(vertrag)
            self.session.commit()
            self.refresh()

    def _bearbeiten(self) -> None:
        vertrag = self._selected()
        if vertrag is None:
            QMessageBox.information(self, "Keine Auswahl", "Bitte zuerst einen Mietvertrag auswählen.")
            return
        dialog = MietvertragDialog(self.session, self, mietvertrag=vertrag)
        if dialog.exec():
            dialog.apply_to(vertrag)
            self.session.commit()
            self.refresh()

    def _loeschen(self) -> None:
        vertrag = self._selected()
        if vertrag is None:
            QMessageBox.information(self, "Keine Auswahl", "Bitte zuerst einen Mietvertrag auswählen.")
            return
        try:
            pruefe_mietvertrag_loeschbar(vertrag)
        except GeschaeftsregelFehler as fehler:
            QMessageBox.warning(self, "Löschen nicht möglich", str(fehler))
            return
        frage = f"Mietvertrag von {vertrag.mieter.name} für {vertrag.mieteinheit.bezeichnung} wirklich löschen?"
        if QMessageBox.question(self, "Löschen", frage) == QMessageBox.StandardButton.Yes:
            self.session.delete(vertrag)
            self.session.commit()
            self.refresh()
