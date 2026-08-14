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

from mietmanager.models import Mieter
from mietmanager.services import GeschaeftsregelFehler, pruefe_mieter_loeschbar
from mietmanager.ui.mieter_dialog import MieterDialog

COLUMNS = ["Name", "E-Mail", "Telefon", "Anzahl Verträge"]


class MieterTab(QWidget):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self._mieter_liste: list[Mieter] = []

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
        self._mieter_liste = list(self.session.scalars(select(Mieter)).all())
        self.table.setRowCount(len(self._mieter_liste))
        for row, mieter in enumerate(self._mieter_liste):
            values = [mieter.name, mieter.email or "", mieter.telefon or "", str(len(mieter.mietvertraege))]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def _selected_mieter(self) -> Mieter | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._mieter_liste):
            return None
        return self._mieter_liste[row]

    def _neu(self) -> None:
        dialog = MieterDialog(self)
        if dialog.exec():
            mieter = Mieter()
            dialog.apply_to(mieter)
            self.session.add(mieter)
            self.session.commit()
            self.refresh()

    def _bearbeiten(self) -> None:
        mieter = self._selected_mieter()
        if mieter is None:
            QMessageBox.information(self, "Kein Mieter ausgewählt", "Bitte zuerst einen Mieter auswählen.")
            return
        dialog = MieterDialog(self, mieter=mieter)
        if dialog.exec():
            dialog.apply_to(mieter)
            self.session.commit()
            self.refresh()

    def _loeschen(self) -> None:
        mieter = self._selected_mieter()
        if mieter is None:
            QMessageBox.information(self, "Kein Mieter ausgewählt", "Bitte zuerst einen Mieter auswählen.")
            return
        try:
            pruefe_mieter_loeschbar(mieter)
        except GeschaeftsregelFehler as fehler:
            QMessageBox.warning(self, "Löschen nicht möglich", str(fehler))
            return
        antwort = QMessageBox.question(self, "Mieter löschen", f"{mieter.name} wirklich löschen?")
        if antwort == QMessageBox.StandardButton.Yes:
            self.session.delete(mieter)
            self.session.commit()
            self.refresh()
