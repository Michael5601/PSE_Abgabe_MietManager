from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mietmanager.models.base import Base


class Umlageschluessel(enum.Enum):
    FLAECHE = "flaeche"
    PERSONEN = "personen"
    EINHEITEN = "einheiten"


class Anrede(enum.Enum):
    HERR = "herr"
    FRAU = "frau"
    KEINE_ANGABE = "keine_angabe"


class Vermieterprofil(Base):
    """Stammdaten des Vermieters."""

    __tablename__ = "vermieterprofil"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    strasse: Mapped[str] = mapped_column(String(120), default="")
    plz: Mapped[str] = mapped_column(String(10), default="")
    ort: Mapped[str] = mapped_column(String(80), default="")
    telefon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)

    def is_complete(self) -> bool:
        return bool(self.name and self.strasse and self.plz and self.ort)


class Immobilie(Base):
    __tablename__ = "immobilien"

    id: Mapped[int] = mapped_column(primary_key=True)
    bezeichnung: Mapped[str] = mapped_column(String(120))
    strasse: Mapped[str] = mapped_column(String(120))
    plz: Mapped[str] = mapped_column(String(10))
    ort: Mapped[str] = mapped_column(String(80))
    baujahr: Mapped[int | None] = mapped_column(nullable=True)

    mieteinheiten: Mapped[list[Mieteinheit]] = relationship(
        back_populates="immobilie", cascade="all, delete-orphan"
    )
    kostenpositionen: Mapped[list[Kostenposition]] = relationship(
        back_populates="immobilie", cascade="all, delete-orphan"
    )
    abrechnungen: Mapped[list[Nebenkostenabrechnung]] = relationship(
        back_populates="immobilie", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Immobilie {self.bezeichnung}>"


class Mieteinheit(Base):
    __tablename__ = "mieteinheiten"

    id: Mapped[int] = mapped_column(primary_key=True)
    immobilie_id: Mapped[int] = mapped_column(ForeignKey("immobilien.id"))
    bezeichnung: Mapped[str] = mapped_column(String(80))
    flaeche_qm: Mapped[float] = mapped_column(Numeric(6, 2))
    zimmeranzahl: Mapped[float] = mapped_column(Numeric(3, 1))

    immobilie: Mapped[Immobilie] = relationship(back_populates="mieteinheiten")
    # Bewusst OHNE delete-orphan-Cascade: Eine Mieteinheit mit bestehenden Mietverträgen soll beim
    # Löschen einen Fehler auslösen (siehe services.regeln.pruefe_mieteinheit_loeschbar), statt die
    # Verträge stillschweigend mitzulöschen.
    mietvertraege: Mapped[list[Mietvertrag]] = relationship(back_populates="mieteinheit")

    def __repr__(self) -> str:
        return f"<Mieteinheit {self.bezeichnung}>"


class Mieter(Base):
    __tablename__ = "mieter"

    id: Mapped[int] = mapped_column(primary_key=True)
    anrede: Mapped[Anrede] = mapped_column(Enum(Anrede), default=Anrede.KEINE_ANGABE)
    vorname: Mapped[str] = mapped_column(String(80))
    nachname: Mapped[str] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    telefon: Mapped[str | None] = mapped_column(String(40), nullable=True)

    mietvertraege: Mapped[list[Mietvertrag]] = relationship(back_populates="mieter")

    @property
    def name(self) -> str:
        return f"{self.vorname} {self.nachname}"

    def __repr__(self) -> str:
        return f"<Mieter {self.name}>"


class Mietvertrag(Base):
    __tablename__ = "mietvertraege"

    id: Mapped[int] = mapped_column(primary_key=True)
    mieteinheit_id: Mapped[int] = mapped_column(ForeignKey("mieteinheiten.id"))
    mieter_id: Mapped[int] = mapped_column(ForeignKey("mieter.id"))
    beginn: Mapped[date] = mapped_column(Date)
    ende: Mapped[date | None] = mapped_column(Date, nullable=True)
    kaltmiete: Mapped[float] = mapped_column(Numeric(8, 2))
    nebenkosten_vorauszahlung: Mapped[float] = mapped_column(Numeric(8, 2))
    kaution: Mapped[float] = mapped_column(Numeric(8, 2))
    personenzahl: Mapped[int] = mapped_column(default=1)

    mieteinheit: Mapped[Mieteinheit] = relationship(back_populates="mietvertraege")
    mieter: Mapped[Mieter] = relationship(back_populates="mietvertraege")
    abrechnungspositionen: Mapped[list[Abrechnungsposition]] = relationship(
        back_populates="mietvertrag"
    )

    def __repr__(self) -> str:
        return f"<Mietvertrag {self.id}>"


class Kostenposition(Base):
    __tablename__ = "kostenpositionen"

    id: Mapped[int] = mapped_column(primary_key=True)
    immobilie_id: Mapped[int] = mapped_column(ForeignKey("immobilien.id"))
    kostenart: Mapped[str] = mapped_column(String(80))
    betrag: Mapped[float] = mapped_column(Numeric(10, 2))
    zeitraum_start: Mapped[date] = mapped_column(Date)
    zeitraum_ende: Mapped[date] = mapped_column(Date)
    umlageschluessel: Mapped[Umlageschluessel] = mapped_column(Enum(Umlageschluessel))

    immobilie: Mapped[Immobilie] = relationship(back_populates="kostenpositionen")

    def __repr__(self) -> str:
        return f"<Kostenposition {self.kostenart} {self.betrag}>"


class Nebenkostenabrechnung(Base):
    __tablename__ = "nebenkostenabrechnungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    immobilie_id: Mapped[int] = mapped_column(ForeignKey("immobilien.id"))
    zeitraum_start: Mapped[date] = mapped_column(Date)
    zeitraum_ende: Mapped[date] = mapped_column(Date)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    immobilie: Mapped[Immobilie] = relationship(back_populates="abrechnungen")
    positionen: Mapped[list[Abrechnungsposition]] = relationship(
        back_populates="abrechnung", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Nebenkostenabrechnung {self.immobilie_id} {self.zeitraum_start}-{self.zeitraum_ende}>"


class Abrechnungsposition(Base):
    """Ergebnis einer Nebenkostenabrechnung für einen einzelnen Mietvertrag."""

    __tablename__ = "abrechnungspositionen"

    id: Mapped[int] = mapped_column(primary_key=True)
    abrechnung_id: Mapped[int] = mapped_column(ForeignKey("nebenkostenabrechnungen.id"))
    mietvertrag_id: Mapped[int] = mapped_column(ForeignKey("mietvertraege.id"))
    anteil_kosten: Mapped[float] = mapped_column(Numeric(10, 2))
    geleistete_vorauszahlung: Mapped[float] = mapped_column(Numeric(10, 2))
    saldo: Mapped[float] = mapped_column(Numeric(10, 2))

    abrechnung: Mapped[Nebenkostenabrechnung] = relationship(back_populates="positionen")
    mietvertrag: Mapped[Mietvertrag] = relationship(back_populates="abrechnungspositionen")
