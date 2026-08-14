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

from mietmanager.models import Kostenposition
from mietmanager.ui.kostenposition_dialog import UMLAGE_LABELS, KostenpositionDialog

COLUMNS = ["Immobilie", "Kostenart", "Betrag", "Zeitraum", "Umlageschlüssel"]


class KostenTab(QWidget):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self._kostenpositionen: list[Kostenposition] = []

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
        self._kostenpositionen = list(self.session.scalars(select(Kostenposition)).all())
        self.table.setRowCount(len(self._kostenpositionen))
        for row, kp in enumerate(self._kostenpositionen):
            values = [
                kp.immobilie.bezeichnung,
                kp.kostenart,
                f"{float(kp.betrag):,.2f} €",
                f"{kp.zeitraum_start.isoformat()} – {kp.zeitraum_ende.isoformat()}",
                UMLAGE_LABELS[kp.umlageschluessel],
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def _selected(self) -> Kostenposition | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._kostenpositionen):
            return None
        return self._kostenpositionen[row]

    def _neu(self) -> None:
        dialog = KostenpositionDialog(self.session, self)
        if dialog.exec():
            kp = Kostenposition()
            dialog.apply_to(kp)
            self.session.add(kp)
            self.session.commit()
            self.refresh()

    def _bearbeiten(self) -> None:
        kp = self._selected()
        if kp is None:
            QMessageBox.information(self, "Keine Auswahl", "Bitte zuerst eine Kostenposition auswählen.")
            return
        dialog = KostenpositionDialog(self.session, self, kostenposition=kp)
        if dialog.exec():
            dialog.apply_to(kp)
            self.session.commit()
            self.refresh()

    def _loeschen(self) -> None:
        kp = self._selected()
        if kp is None:
            QMessageBox.information(self, "Keine Auswahl", "Bitte zuerst eine Kostenposition auswählen.")
            return
        frage = f"Kostenposition '{kp.kostenart}' wirklich löschen?"
        if QMessageBox.question(self, "Löschen", frage) == QMessageBox.StandardButton.Yes:
            self.session.delete(kp)
            self.session.commit()
            self.refresh()
