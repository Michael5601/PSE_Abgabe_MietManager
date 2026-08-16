"""Unit-Tests für den PDF-Export der Nebenkostenabrechnung (services/pdf_export.py)."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mietmanager.models import (
    Anrede,
    Base,
    Immobilie,
    Kostenposition,
    Mieteinheit,
    Mieter,
    Mietvertrag,
    Umlageschluessel,
    Vermieterprofil,
)
from mietmanager.services import GeschaeftsregelFehler, erstelle_abrechnung, exportiere_abrechnung
from mietmanager.services.pdf_export import _get_anredetext, _get_dateiname


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def _profil_vollstaendig() -> Vermieterprofil:
    return Vermieterprofil(name="Max Muster", strasse="Musterweg 1", plz="12345", ort="Musterstadt")


def _abrechnung_mit_einer_position(
    session, nachname: str = "Muster", vorname: str = "Erika", nk_vorauszahlung: float = 100
):
    immobilie = Immobilie(bezeichnung="Haus", strasse="Str. 1", plz="00000", ort="Ort")
    einheit = Mieteinheit(immobilie=immobilie, bezeichnung="Whg", flaeche_qm=50, zimmeranzahl=2)
    mieter = Mieter(anrede=Anrede.FRAU, vorname=vorname, nachname=nachname)
    vertrag = Mietvertrag(
        mieteinheit=einheit, mieter=mieter, beginn=date(2024, 1, 1),
        kaltmiete=500, nebenkosten_vorauszahlung=nk_vorauszahlung, kaution=1500, personenzahl=1,
    )
    session.add_all([immobilie, einheit, mieter, vertrag])
    session.flush()
    kostenposition = Kostenposition(
        immobilie=immobilie, kostenart="Heizung", betrag=1200,
        zeitraum_start=date(2024, 1, 1), zeitraum_ende=date(2024, 12, 31),
        umlageschluessel=Umlageschluessel.FLAECHE,
    )
    session.add(kostenposition)
    session.flush()
    return erstelle_abrechnung(session, immobilie, date(2024, 1, 1), date(2024, 12, 31))


def test_anredetext_herr() -> None:
    mieter = Mieter(anrede=Anrede.HERR, vorname="Max", nachname="Schmidt")
    assert _get_anredetext(mieter) == "Sehr geehrter Herr Schmidt,"


def test_anredetext_frau() -> None:
    mieter = Mieter(anrede=Anrede.FRAU, vorname="Erika", nachname="Schmidt")
    assert _get_anredetext(mieter) == "Sehr geehrte Frau Schmidt,"


def test_anredetext_keine_angabe() -> None:
    mieter = Mieter(anrede=Anrede.KEINE_ANGABE, vorname="Alex", nachname="Schmidt")
    assert _get_anredetext(mieter) == "Sehr geehrte Damen und Herren,"


def test_dateiname_enthaelt_jahr_und_mieternamen(session) -> None:
    abrechnung = _abrechnung_mit_einer_position(session, nachname="Müller", vorname="Anna")
    dateiname = _get_dateiname(abrechnung.positionen[0])
    assert dateiname == "Nebenkostenabrechnung_2024_Müller_Anna.pdf"


def test_dateiname_ersetzt_dateisystem_unsichere_zeichen(session) -> None:
    abrechnung = _abrechnung_mit_einer_position(session, nachname="O'Brien/Smith", vorname="Jean")
    dateiname = _get_dateiname(abrechnung.positionen[0])
    # "/" und "'" sind keine \w-Zeichen und werden von der Sanitisierung durch "_" ersetzt.
    assert dateiname == "Nebenkostenabrechnung_2024_O_Brien_Smith_Jean.pdf"


def test_exportiere_abrechnung_lehnt_unvollstaendiges_profil_ab(session, tmp_path) -> None:
    abrechnung = _abrechnung_mit_einer_position(session)
    unvollstaendiges_profil = Vermieterprofil(name="", strasse="", plz="", ort="")
    with pytest.raises(GeschaeftsregelFehler):
        exportiere_abrechnung(abrechnung, unvollstaendiges_profil, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_exportiere_abrechnung_erzeugt_eine_pdf_datei_je_mietvertrag(session, tmp_path) -> None:
    abrechnung = _abrechnung_mit_einer_position(session)
    erzeugte_dateien = exportiere_abrechnung(abrechnung, _profil_vollstaendig(), tmp_path)

    assert len(erzeugte_dateien) == 1
    pfad = erzeugte_dateien[0]
    assert pfad.exists()
    assert pfad.suffix == ".pdf"
    assert pfad.stat().st_size > 0


def test_exportiere_abrechnung_bei_nachzahlung_mit_iban(session, tmp_path) -> None:
    # Vorauszahlung (50 * 12 = 600) < Kostenanteil (1200) => positiver Saldo (Nachzahlung).
    abrechnung = _abrechnung_mit_einer_position(session, nk_vorauszahlung=50)
    profil = _profil_vollstaendig()
    profil.iban = "DE02120300000000202051"

    erzeugte_dateien = exportiere_abrechnung(abrechnung, profil, tmp_path)

    assert erzeugte_dateien[0].stat().st_size > 0


def test_exportiere_abrechnung_bei_rueckerstattung(session, tmp_path) -> None:
    # Vorauszahlung (200 * 12 = 2400) > Kostenanteil (1200) => negativer Saldo (Rückerstattung).
    abrechnung = _abrechnung_mit_einer_position(session, nk_vorauszahlung=200)

    erzeugte_dateien = exportiere_abrechnung(abrechnung, _profil_vollstaendig(), tmp_path)

    assert erzeugte_dateien[0].stat().st_size > 0
