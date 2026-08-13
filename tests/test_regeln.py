"""Unit-Tests für die zentralen Geschäftsregeln (services/regeln.py).

Die getesteten Funktionen kennen kein Qt und keine Datenbank -- die Modelle werden hier rein als
Python-Objektgraph aufgebaut (SQLAlchemy pflegt back_populates-Listen bereits ohne Session-Flush).
"""

from datetime import date

import pytest

from mietmanager.models import Immobilie, Mieteinheit, Mieter, Mietvertrag, Vermieterprofil
from mietmanager.services import (
    GeschaeftsregelFehler,
    pruefe_immobilie_loeschbar,
    pruefe_keine_ueberlappung,
    pruefe_mieteinheit_loeschbar,
    pruefe_mieter_loeschbar,
    pruefe_profil_vollstaendig,
    pruefe_vertragszeitraum,
)


def _mieteinheit() -> Mieteinheit:
    immobilie = Immobilie(bezeichnung="Testhaus", strasse="Teststr. 1", plz="00000", ort="Testort")
    return Mieteinheit(immobilie=immobilie, bezeichnung="Whg 1", flaeche_qm=50, zimmeranzahl=2)


def _mieter(vorname="Anna", nachname="Test") -> Mieter:
    return Mieter(vorname=vorname, nachname=nachname)


def _vertrag(mieteinheit, mieter, beginn, ende=None) -> Mietvertrag:
    return Mietvertrag(
        mieteinheit=mieteinheit,
        mieter=mieter,
        beginn=beginn,
        ende=ende,
        kaltmiete=500,
        nebenkosten_vorauszahlung=150,
        kaution=1500,
        personenzahl=1,
    )


class TestVertragszeitraum:
    def test_gueltiger_zeitraum_wird_akzeptiert(self) -> None:
        pruefe_vertragszeitraum(date(2025, 1, 1), date(2025, 12, 31))

    def test_unbefristeter_vertrag_ohne_ende_wird_akzeptiert(self) -> None:
        pruefe_vertragszeitraum(date(2025, 1, 1), None)

    def test_ende_vor_beginn_wird_abgelehnt(self) -> None:
        with pytest.raises(GeschaeftsregelFehler):
            pruefe_vertragszeitraum(date(2025, 6, 1), date(2025, 1, 1))

    def test_ende_gleich_beginn_wird_abgelehnt(self) -> None:
        with pytest.raises(GeschaeftsregelFehler):
            pruefe_vertragszeitraum(date(2025, 1, 1), date(2025, 1, 1))


class TestKeineUeberlappung:
    def test_kein_konflikt_bei_nicht_ueberlappenden_zeitraeumen(self) -> None:
        einheit = _mieteinheit()
        bestehender = _vertrag(einheit, _mieter(), date(2023, 1, 1), date(2023, 12, 31))
        pruefe_keine_ueberlappung([bestehender], date(2024, 1, 1), None)

    def test_konflikt_bei_ueberlappenden_zeitraeumen(self) -> None:
        einheit = _mieteinheit()
        bestehender = _vertrag(einheit, _mieter("Bernd", "Bestand"), date(2024, 1, 1), None)
        with pytest.raises(GeschaeftsregelFehler, match="Bernd Bestand"):
            pruefe_keine_ueberlappung([bestehender], date(2024, 6, 1), date(2024, 8, 1))

    def test_eigener_vertrag_wird_beim_bearbeiten_ausgenommen(self) -> None:
        einheit = _mieteinheit()
        bestehender = _vertrag(einheit, _mieter(), date(2024, 1, 1), None)
        bestehender.id = 42
        # Ohne Ausnahme würde der eigene (unveränderte) Vertrag selbst als Konflikt erkannt.
        pruefe_keine_ueberlappung(
            [bestehender], date(2024, 1, 1), None, ausgenommen_vertrag_id=42
        )


class TestLoeschregeln:
    def test_immobilie_ohne_vertraege_ist_loeschbar(self) -> None:
        einheit = _mieteinheit()
        pruefe_immobilie_loeschbar(einheit.immobilie)

    def test_immobilie_mit_vertrag_ist_nicht_loeschbar(self) -> None:
        einheit = _mieteinheit()
        _vertrag(einheit, _mieter(), date(2024, 1, 1), None)
        with pytest.raises(GeschaeftsregelFehler):
            pruefe_immobilie_loeschbar(einheit.immobilie)

    def test_mieteinheit_ohne_vertrag_ist_loeschbar(self) -> None:
        einheit = _mieteinheit()
        pruefe_mieteinheit_loeschbar(einheit)

    def test_mieteinheit_mit_vertrag_ist_nicht_loeschbar(self) -> None:
        einheit = _mieteinheit()
        _vertrag(einheit, _mieter(), date(2024, 1, 1), None)
        with pytest.raises(GeschaeftsregelFehler):
            pruefe_mieteinheit_loeschbar(einheit)

    def test_mieter_ohne_vertrag_ist_loeschbar(self) -> None:
        pruefe_mieter_loeschbar(_mieter())

    def test_mieter_mit_vertrag_ist_nicht_loeschbar(self) -> None:
        mieter = _mieter()
        _vertrag(_mieteinheit(), mieter, date(2024, 1, 1), None)
        with pytest.raises(GeschaeftsregelFehler):
            pruefe_mieter_loeschbar(mieter)


class TestProfilVollstaendigkeit:
    def test_vollstaendiges_profil_wird_akzeptiert(self) -> None:
        profil = Vermieterprofil(name="Max Muster", strasse="Musterweg 1", plz="12345", ort="Musterstadt")
        pruefe_profil_vollstaendig(profil)

    def test_unvollstaendiges_profil_wird_abgelehnt(self) -> None:
        profil = Vermieterprofil(name="", strasse="", plz="", ort="")
        with pytest.raises(GeschaeftsregelFehler):
            pruefe_profil_vollstaendig(profil)
