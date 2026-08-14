from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from mietmanager.models import Immobilie, Mieteinheit
from mietmanager.services import GeschaeftsregelFehler, pruefe_immobilie_loeschbar, pruefe_mieteinheit_loeschbar
from mietmanager.ui.immobilie_dialog import ImmobilieDialog
from mietmanager.ui.mieteinheit_dialog import MieteinheitDialog

ENTITY_ROLE = Qt.ItemDataRole.UserRole


class ImmobilienTab(QWidget):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Objekt / Einheit", "Fläche (qm)", "Zimmer", "Mieter"])
        self.tree.doubleClicked.connect(self._bearbeiten)

        neue_immobilie_btn = QPushButton("＋ Neue Immobilie…")
        neue_immobilie_btn.setObjectName("primaryButton")
        neue_immobilie_btn.clicked.connect(self._neue_immobilie)
        neue_einheit_btn = QPushButton("＋ Neue Mieteinheit…")
        neue_einheit_btn.clicked.connect(self._neue_mieteinheit)
        bearbeiten_btn = QPushButton("✎ Bearbeiten…")
        bearbeiten_btn.clicked.connect(self._bearbeiten)
        loeschen_btn = QPushButton("🗑 Löschen")
        loeschen_btn.setObjectName("dangerButton")
        loeschen_btn.clicked.connect(self._loeschen)
        refresh_btn = QPushButton("⟳ Aktualisieren")
        refresh_btn.clicked.connect(self.refresh)

        btn_row = QHBoxLayout()
        btn_row.addWidget(neue_immobilie_btn)
        btn_row.addWidget(neue_einheit_btn)
        btn_row.addWidget(bearbeiten_btn)
        btn_row.addWidget(loeschen_btn)
        btn_row.addStretch()
        btn_row.addWidget(refresh_btn)

        layout = QVBoxLayout()
        layout.addLayout(btn_row)
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        immobilien = self.session.scalars(select(Immobilie)).all()
        for immobilie in immobilien:
            top = QTreeWidgetItem(
                [f"{immobilie.bezeichnung} ({immobilie.strasse}, {immobilie.plz} {immobilie.ort})"]
            )
            top.setData(0, ENTITY_ROLE, ("immobilie", immobilie.id))
            for einheit in immobilie.mieteinheiten:
                aktueller_mieter = next(
                    (v.mieter.name for v in einheit.mietvertraege if v.ende is None), "frei"
                )
                child = QTreeWidgetItem(
                    [
                        einheit.bezeichnung,
                        str(einheit.flaeche_qm),
                        str(einheit.zimmeranzahl),
                        aktueller_mieter,
                    ]
                )
                child.setData(0, ENTITY_ROLE, ("mieteinheit", einheit.id))
                top.addChild(child)
            self.tree.addTopLevelItem(top)
        self.tree.expandAll()

    def _selected_entity(self):
        items = self.tree.selectedItems()
        if not items:
            return None, None
        kind, entity_id = items[0].data(0, ENTITY_ROLE)
        if kind == "immobilie":
            return "immobilie", self.session.get(Immobilie, entity_id)
        return "mieteinheit", self.session.get(Mieteinheit, entity_id)

    def _neue_immobilie(self) -> None:
        dialog = ImmobilieDialog(self)
        if dialog.exec():
            immobilie = Immobilie()
            dialog.apply_to(immobilie)
            self.session.add(immobilie)
            self.session.commit()
            self.refresh()

    def _neue_mieteinheit(self) -> None:
        kind, entity = self._selected_entity()
        if kind == "immobilie":
            immobilie = entity
        elif kind == "mieteinheit":
            immobilie = entity.immobilie
        else:
            QMessageBox.information(
                self,
                "Keine Immobilie ausgewählt",
                "Bitte zuerst eine Immobilie (oder eine ihrer Einheiten) auswählen.",
            )
            return
        dialog = MieteinheitDialog(self)
        if dialog.exec():
            einheit = Mieteinheit(immobilie=immobilie)
            dialog.apply_to(einheit)
            self.session.add(einheit)
            self.session.commit()
            self.refresh()

    def _bearbeiten(self) -> None:
        kind, entity = self._selected_entity()
        if entity is None:
            QMessageBox.information(
                self, "Keine Auswahl", "Bitte zuerst eine Immobilie oder Mieteinheit auswählen."
            )
            return
        dialog = ImmobilieDialog(self, immobilie=entity) if kind == "immobilie" else MieteinheitDialog(
            self, mieteinheit=entity
        )
        if dialog.exec():
            dialog.apply_to(entity)
            self.session.commit()
            self.refresh()

    def _loeschen(self) -> None:
        kind, entity = self._selected_entity()
        if entity is None:
            QMessageBox.information(
                self, "Keine Auswahl", "Bitte zuerst eine Immobilie oder Mieteinheit auswählen."
            )
            return
        try:
            if kind == "immobilie":
                pruefe_immobilie_loeschbar(entity)
                frage = f"Immobilie '{entity.bezeichnung}' wirklich löschen?"
            else:
                pruefe_mieteinheit_loeschbar(entity)
                frage = f"Mieteinheit '{entity.bezeichnung}' wirklich löschen?"
        except GeschaeftsregelFehler as fehler:
            QMessageBox.warning(self, "Löschen nicht möglich", str(fehler))
            return

        if QMessageBox.question(self, "Löschen", frage) == QMessageBox.StandardButton.Yes:
            self.session.delete(entity)
            self.session.commit()
            self.refresh()
