"""Unit-Tests für die Berechnungslogik der Nebenkostenabrechnung (services/abrechnung.py)."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mietmanager.models import (
    Base,
    Immobilie,
    Kostenposition,
    Mieteinheit,
    Mieter,
    Mietvertrag,
    Nebenkostenabrechnung,
    Umlageschluessel,
)
from mietmanager.services import AbrechnungsFehler, erstelle_abrechnung, lade_abrechnungen
from mietmanager.services.abrechnung import get_positionsdetails


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def _immobilie(db: Session) -> Immobilie:
    immobilie = Immobilie(bezeichnung="Testhaus", strasse="Teststr. 1", plz="00000", ort="Testort")
    db.add(immobilie)
    db.flush()
    return immobilie


def _einheit(db: Session, immobilie: Immobilie, flaeche: float = 50) -> Mieteinheit:
    einheit = Mieteinheit(immobilie=immobilie, bezeichnung="Whg", flaeche_qm=flaeche, zimmeranzahl=2)
    db.add(einheit)
    db.flush()
    return einheit


def _mieter(db: Session, vorname: str = "Anna", nachname: str = "Test") -> Mieter:
    mieter = Mieter(vorname=vorname, nachname=nachname)
    db.add(mieter)
    db.flush()
    return mieter


def _vertrag(
    db: Session,
    einheit: Mieteinheit,
    mieter: Mieter,
    beginn: date,
    ende: date | None = None,
    kaltmiete: float = 500,
    nk_vorauszahlung: float = 150,
    personenzahl: int = 1,
) -> Mietvertrag:
    vertrag = Mietvertrag(
        mieteinheit=einheit,
        mieter=mieter,
        beginn=beginn,
        ende=ende,
        kaltmiete=kaltmiete,
        nebenkosten_vorauszahlung=nk_vorauszahlung,
        kaution=1500,
        personenzahl=personenzahl,
    )
    db.add(vertrag)
    db.flush()
    return vertrag


def _kostenposition(
    db: Session,
    immobilie: Immobilie,
    betrag: float,
    start: date,
    ende: date,
    schluessel: Umlageschluessel = Umlageschluessel.FLAECHE,
    art: str = "Heizung",
) -> Kostenposition:
    kp = Kostenposition(
        immobilie=immobilie,
        kostenart=art,
        betrag=betrag,
        zeitraum_start=start,
        zeitraum_ende=ende,
        umlageschluessel=schluessel,
    )
    db.add(kp)
    db.flush()
    return kp


def test_start_nach_ende_wird_abgelehnt(session) -> None:
    immobilie = _immobilie(session)
    with pytest.raises(AbrechnungsFehler):
        erstelle_abrechnung(session, immobilie, date(2024, 12, 31), date(2024, 1, 1))


def test_ohne_kostenpositionen_wird_abgelehnt(session) -> None:
    immobilie = _immobilie(session)
    einheit = _einheit(session, immobilie)
    mieter = _mieter(session)
    _vertrag(session, einheit, mieter, date(2024, 1, 1))
    with pytest.raises(AbrechnungsFehler, match="Kostenpositionen"):
        erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))


def test_ohne_aktive_vertraege_wird_abgelehnt(session) -> None:
    immobilie = _immobilie(session)
    _kostenposition(session, immobilie, 1200, date(2024, 1, 1), date(2024, 12, 31))
    with pytest.raises(AbrechnungsFehler, match="Mietverträge"):
        erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))


def test_gesamtgewicht_null_wird_abgelehnt(session) -> None:
    # Umlageschluessel PERSONEN mit personenzahl=0 auf dem einzigen aktiven Vertrag ergibt ein
    # Gesamtgewicht von 0, wodurch die Kostenposition nicht verteilt werden kann.
    immobilie = _immobilie(session)
    einheit = _einheit(session, immobilie)
    _vertrag(session, einheit, _mieter(session), date(2024, 1, 1), personenzahl=0)
    _kostenposition(session, immobilie, 1200, date(2024, 1, 1), date(2024, 12, 31), Umlageschluessel.PERSONEN)
    with pytest.raises(AbrechnungsFehler, match="Gesamtgewicht 0"):
        erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))


def test_kostenposition_ausserhalb_des_zeitraums_wird_ignoriert(session) -> None:
    immobilie = _immobilie(session)
    einheit = _einheit(session, immobilie)
    mieter = _mieter(session)
    _vertrag(session, einheit, mieter, date(2024, 1, 1))
    _kostenposition(session, immobilie, 1200, date(2023, 1, 1), date(2023, 12, 31))
    with pytest.raises(AbrechnungsFehler, match="Kostenpositionen"):
        erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))


def test_verteilung_nach_flaeche(session) -> None:
    immobilie = _immobilie(session)
    einheit1 = _einheit(session, immobilie, flaeche=50)
    einheit2 = _einheit(session, immobilie, flaeche=50)
    vertrag1 = _vertrag(session, einheit1, _mieter(session, "Anna", "Eins"), date(2024, 1, 1), nk_vorauszahlung=100)
    vertrag2 = _vertrag(session, einheit2, _mieter(session, "Bernd", "Zwei"), date(2024, 1, 1), nk_vorauszahlung=100)
    _kostenposition(session, immobilie, 1200, date(2024, 1, 1), date(2024, 12, 31), Umlageschluessel.FLAECHE)

    abrechnung = erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))

    assert len(abrechnung.positionen) == 2
    positionen_nach_vertrag = {p.mietvertrag_id: p for p in abrechnung.positionen}
    for vertrag in (vertrag1, vertrag2):
        position = positionen_nach_vertrag[vertrag.id]
        assert float(position.anteil_kosten) == 600.0
        assert float(position.geleistete_vorauszahlung) == 1200.0
        assert float(position.saldo) == pytest.approx(-600.0)


def test_verteilung_nach_personenzahl(session) -> None:
    immobilie = _immobilie(session)
    einheit1 = _einheit(session, immobilie)
    einheit2 = _einheit(session, immobilie)
    vertrag1 = _vertrag(session, einheit1, _mieter(session, "Anna", "Eins"), date(2024, 1, 1), personenzahl=1)
    vertrag2 = _vertrag(session, einheit2, _mieter(session, "Bernd", "Zwei"), date(2024, 1, 1), personenzahl=3)
    _kostenposition(session, immobilie, 800, date(2024, 1, 1), date(2024, 12, 31), Umlageschluessel.PERSONEN)

    abrechnung = erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))

    positionen_nach_vertrag = {p.mietvertrag_id: p for p in abrechnung.positionen}
    assert float(positionen_nach_vertrag[vertrag1.id].anteil_kosten) == 200.0
    assert float(positionen_nach_vertrag[vertrag2.id].anteil_kosten) == 600.0


def test_verteilung_nach_einheiten_ist_gleichmaessig(session) -> None:
    immobilie = _immobilie(session)
    einheit1 = _einheit(session, immobilie, flaeche=30)
    einheit2 = _einheit(session, immobilie, flaeche=90)
    vertrag1 = _vertrag(session, einheit1, _mieter(session, "Anna", "Eins"), date(2024, 1, 1))
    vertrag2 = _vertrag(session, einheit2, _mieter(session, "Bernd", "Zwei"), date(2024, 1, 1))
    _kostenposition(session, immobilie, 500, date(2024, 1, 1), date(2024, 12, 31), Umlageschluessel.EINHEITEN)

    abrechnung = erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))

    positionen_nach_vertrag = {p.mietvertrag_id: p for p in abrechnung.positionen}
    assert float(positionen_nach_vertrag[vertrag1.id].anteil_kosten) == 250.0
    assert float(positionen_nach_vertrag[vertrag2.id].anteil_kosten) == 250.0


def test_saldo_positiv_bedeutet_nachzahlung(session) -> None:
    immobilie = _immobilie(session)
    einheit = _einheit(session, immobilie)
    _vertrag(session, einheit, _mieter(session), date(2024, 1, 1), nk_vorauszahlung=10)
    _kostenposition(session, immobilie, 1200, date(2024, 1, 1), date(2024, 12, 31))

    abrechnung = erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))

    position = abrechnung.positionen[0]
    assert float(position.anteil_kosten) == 1200.0
    assert float(position.geleistete_vorauszahlung) == 120.0
    assert float(position.saldo) == pytest.approx(1080.0)


def test_beendeter_vertrag_ausserhalb_zeitraum_wird_nicht_beruecksichtigt(session) -> None:
    immobilie = _immobilie(session)
    einheit = _einheit(session, immobilie)
    _vertrag(session, einheit, _mieter(session), date(2020, 1, 1), ende=date(2020, 12, 31))
    _kostenposition(session, immobilie, 1200, date(2024, 1, 1), date(2024, 12, 31))
    with pytest.raises(AbrechnungsFehler, match="Mietverträge"):
        erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))


def test_persistiert_abrechnung_in_datenbank(session) -> None:
    immobilie = _immobilie(session)
    einheit = _einheit(session, immobilie)
    _vertrag(session, einheit, _mieter(session), date(2024, 1, 1))
    _kostenposition(session, immobilie, 1200, date(2024, 1, 1), date(2024, 12, 31))

    abrechnung = erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))

    wieder_geladen = session.get(Nebenkostenabrechnung, abrechnung.id)
    assert wieder_geladen is not None
    assert len(wieder_geladen.positionen) == 1


def test_get_positionsdetails_liefert_kostenart_und_anteil_je_kostenposition(session) -> None:
    immobilie = _immobilie(session)
    einheit = _einheit(session, immobilie)
    vertrag = _vertrag(session, einheit, _mieter(session), date(2024, 1, 1))
    _kostenposition(session, immobilie, 600, date(2024, 1, 1), date(2024, 12, 31), art="Heizung")
    _kostenposition(session, immobilie, 400, date(2024, 1, 1), date(2024, 12, 31), art="Wasser")

    abrechnung = erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))
    details = get_positionsdetails(abrechnung, vertrag)

    details_by_kostenart = dict(details)
    assert details_by_kostenart["Heizung"] == 600.0
    assert details_by_kostenart["Wasser"] == 400.0


def test_lade_abrechnungen_liefert_leere_liste_ohne_abrechnungen(session) -> None:
    immobilie = _immobilie(session)
    assert lade_abrechnungen(session, immobilie.id) == []


def test_lade_abrechnungen_liefert_nur_abrechnungen_der_gewaehlten_immobilie(session) -> None:
    immobilie1 = _immobilie(session)
    einheit1 = _einheit(session, immobilie1)
    _vertrag(session, einheit1, _mieter(session), date(2024, 1, 1))
    _kostenposition(session, immobilie1, 1200, date(2024, 1, 1), date(2024, 12, 31))
    erstelle_abrechnung(session, immobilie1, date(2024, 1, 1), date(2024, 12, 31))

    immobilie2 = _immobilie(session)
    einheit2 = _einheit(session, immobilie2)
    _vertrag(session, einheit2, _mieter(session), date(2024, 1, 1))
    _kostenposition(session, immobilie2, 800, date(2024, 1, 1), date(2024, 12, 31))
    erstelle_abrechnung(session, immobilie2, date(2024, 1, 1), date(2024, 12, 31))

    abrechnungen = lade_abrechnungen(session, immobilie1.id)

    assert len(abrechnungen) == 1
    assert abrechnungen[0].immobilie_id == immobilie1.id


def test_lade_abrechnungen_sortiert_neuesten_zeitraum_zuerst(session) -> None:
    immobilie = _immobilie(session)
    einheit = _einheit(session, immobilie)
    _vertrag(session, einheit, _mieter(session), date(2022, 1, 1))
    _kostenposition(session, immobilie, 1200, date(2022, 1, 1), date(2022, 12, 31))
    _kostenposition(session, immobilie, 1200, date(2023, 1, 1), date(2023, 12, 31))
    erstelle_abrechnung(session, immobilie, date(2022, 1, 1), date(2022, 12, 31))
    erstelle_abrechnung(session, immobilie, date(2023, 1, 1), date(2023, 12, 31))

    abrechnungen = lade_abrechnungen(session, immobilie.id)

    assert [a.zeitraum_start for a in abrechnungen] == [date(2023, 1, 1), date(2022, 1, 1)]