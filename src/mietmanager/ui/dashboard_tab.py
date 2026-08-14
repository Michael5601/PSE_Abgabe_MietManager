from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from mietmanager.models import Immobilie, Mieteinheit, Mietvertrag


class _StatCard(QFrame):
    def __init__(self, titel: str) -> None:
        super().__init__()
        self.setObjectName("statCard")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(31, 36, 48, 40))
        self.setGraphicsEffect(shadow)

        self.value_label = QLabel("–")
        self.value_label.setObjectName("statValue")
        self.title_label = QLabel(titel)
        self.title_label.setObjectName("statTitle")
        self.title_label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)
        self.setLayout(layout)

    def set_value(self, text: str) -> None:
        self.value_label.setText(text)


class DashboardTab(QWidget):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session

        self.card_immobilien = _StatCard("Immobilien")
        self.card_einheiten = _StatCard("Mieteinheiten")
        self.card_leerstand = _StatCard("davon leerstehend")
        self.card_vertraege = _StatCard("aktive Mietverträge")
        self.card_einnahmen = _StatCard("Kaltmiete-Einnahmen/Monat")

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for card in (
            self.card_immobilien,
            self.card_einheiten,
            self.card_leerstand,
            self.card_vertraege,
            self.card_einnahmen,
        ):
            cards_row.addWidget(card)

        refresh_btn = QPushButton("⟳ Aktualisieren")
        refresh_btn.clicked.connect(self.refresh)

        layout = QVBoxLayout()
        layout.addLayout(cards_row)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        self.setLayout(layout)

        self.refresh()

    def refresh(self) -> None:
        immobilien = self.session.scalars(select(Immobilie)).all()
        einheiten = self.session.scalars(select(Mieteinheit)).all()
        aktive_vertraege = [
            v for v in self.session.scalars(select(Mietvertrag)).all() if v.ende is None
        ]
        vermietete_einheiten_ids = {v.mieteinheit_id for v in aktive_vertraege}
        leerstand = [e for e in einheiten if e.id not in vermietete_einheiten_ids]
        einnahmen = sum(float(v.kaltmiete) for v in aktive_vertraege)

        self.card_immobilien.set_value(str(len(immobilien)))
        self.card_einheiten.set_value(str(len(einheiten)))
        self.card_leerstand.set_value(str(len(leerstand)))
        self.card_vertraege.set_value(str(len(aktive_vertraege)))
        self.card_einnahmen.set_value(f"{einnahmen:,.2f} €")
