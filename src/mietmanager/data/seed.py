"""Testdaten, damit die Anwendung nach der Installation sofort sinnvoll nutzbar ist."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from mietmanager.models import (
    Anrede,
    Immobilie,
    Kostenposition,
    Mieteinheit,
    Mieter,
    Mietvertrag,
    Umlageschluessel,
    Vermieterprofil,
)


def seed_if_empty(session: Session) -> bool:
    if session.scalar(select(Immobilie.id).limit(1)) is not None:
        return False

    haus = Immobilie(
        bezeichnung="Mehrfamilienhaus Bahnhofstraße 12",
        strasse="Bahnhofstraße 12",
        plz="04109",
        ort="Leipzig",
        baujahr=1998,
    )
    doppelhaus = Immobilie(
        bezeichnung="Doppelhaushälfte Gartenweg 4",
        strasse="Gartenweg 4",
        plz="04155",
        ort="Leipzig",
        baujahr=1965,
    )

    whg1 = Mieteinheit(immobilie=haus, bezeichnung="Whg 1 EG links", flaeche_qm=62.5, zimmeranzahl=2.5)
    whg2 = Mieteinheit(immobilie=haus, bezeichnung="Whg 2 EG rechts", flaeche_qm=58.0, zimmeranzahl=2.0)
    whg3 = Mieteinheit(immobilie=haus, bezeichnung="Whg 3 OG links", flaeche_qm=75.0, zimmeranzahl=3.0)
    erdgeschoss = Mieteinheit(immobilie=doppelhaus, bezeichnung="Erdgeschoss", flaeche_qm=90.0, zimmeranzahl=4.0)

    anna = Mieter(
        anrede=Anrede.FRAU, vorname="Anna", nachname="Schmidt",
        email="anna.schmidt@example.com", telefon="0341 1234567",
    )
    bernd = Mieter(
        anrede=Anrede.HERR, vorname="Bernd", nachname="Wolf",
        email="bernd.wolf@example.com", telefon="0341 2345678",
    )
    carla = Mieter(
        anrede=Anrede.FRAU, vorname="Carla", nachname="Fischer",
        email="carla.fischer@example.com", telefon="0341 3456789",
    )
    daniel = Mieter(
        anrede=Anrede.HERR, vorname="Daniel", nachname="Krüger",
        email="daniel.krueger@example.com", telefon="0341 4567890",
    )

    vertrag1 = Mietvertrag(
        mieteinheit=whg1, mieter=anna, beginn=date(2023, 1, 1),
        kaltmiete=550, nebenkosten_vorauszahlung=150, kaution=1650, personenzahl=1,
    )
    vertrag2 = Mietvertrag(
        mieteinheit=whg2, mieter=bernd, beginn=date(2022, 6, 1),
        kaltmiete=510, nebenkosten_vorauszahlung=140, kaution=1530, personenzahl=2,
    )
    vertrag3 = Mietvertrag(
        mieteinheit=whg3, mieter=carla, beginn=date(2021, 9, 1),
        kaltmiete=680, nebenkosten_vorauszahlung=180, kaution=2040, personenzahl=3,
    )
    vertrag4 = Mietvertrag(
        mieteinheit=erdgeschoss, mieter=daniel, beginn=date(2020, 3, 1),
        kaltmiete=850, nebenkosten_vorauszahlung=220, kaution=2550, personenzahl=4,
    )

    kostenpositionen_haus = [
        Kostenposition(
            immobilie=haus, kostenart="Grundsteuer", betrag=1200.00,
            zeitraum_start=date(2025, 1, 1), zeitraum_ende=date(2025, 12, 31),
            umlageschluessel=Umlageschluessel.FLAECHE,
        ),
        Kostenposition(
            immobilie=haus, kostenart="Wasser/Abwasser", betrag=900.00,
            zeitraum_start=date(2025, 1, 1), zeitraum_ende=date(2025, 12, 31),
            umlageschluessel=Umlageschluessel.PERSONEN,
        ),
        Kostenposition(
            immobilie=haus, kostenart="Müllabfuhr", betrag=450.00,
            zeitraum_start=date(2025, 1, 1), zeitraum_ende=date(2025, 12, 31),
            umlageschluessel=Umlageschluessel.PERSONEN,
        ),
        Kostenposition(
            immobilie=haus, kostenart="Hausversicherung", betrag=600.00,
            zeitraum_start=date(2025, 1, 1), zeitraum_ende=date(2025, 12, 31),
            umlageschluessel=Umlageschluessel.FLAECHE,
        ),
        Kostenposition(
            immobilie=haus, kostenart="Hausmeister/Gartenpflege", betrag=720.00,
            zeitraum_start=date(2025, 1, 1), zeitraum_ende=date(2025, 12, 31),
            umlageschluessel=Umlageschluessel.EINHEITEN,
        ),
    ]
    kostenpositionen_doppelhaus = [
        Kostenposition(
            immobilie=doppelhaus, kostenart="Grundsteuer", betrag=400.00,
            zeitraum_start=date(2025, 1, 1), zeitraum_ende=date(2025, 12, 31),
            umlageschluessel=Umlageschluessel.FLAECHE,
        ),
        Kostenposition(
            immobilie=doppelhaus, kostenart="Wasser/Abwasser", betrag=350.00,
            zeitraum_start=date(2025, 1, 1), zeitraum_ende=date(2025, 12, 31),
            umlageschluessel=Umlageschluessel.PERSONEN,
        ),
    ]

    profil = Vermieterprofil(
        id=1,
        name="Max Mustermann",
        strasse="Musterstraße 1",
        plz="04109",
        ort="Leipzig",
        telefon="0341 9876543",
        email="verwaltung@example.com",
        iban="DE12 3456 7890 1234 5678 90",
    )

    session.add_all(
        [haus, doppelhaus, vertrag1, vertrag2, vertrag3, vertrag4, profil]
        + kostenpositionen_haus
        + kostenpositionen_doppelhaus
    )
    session.commit()
    return True
