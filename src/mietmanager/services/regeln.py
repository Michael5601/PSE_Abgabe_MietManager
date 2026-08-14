"""Zentrale Geschäftsregeln (siehe Spezifikationsdokument, Abschnitt 3).

Diese Funktionen kennen kein Qt und keine Datenbank-Session-Details. Sie prüfen ausschließlich
die übergebenen Werte. Damit lassen sich die Regeln isoliert testen.
"""

from datetime import date as date_type
from typing import Iterable

MAX_DATE = date_type(9999, 12, 31)


class GeschaeftsregelFehler(Exception):
    """Wird ausgelöst, wenn eine Aktion gegen eine Geschäftsregel verstößt."""


def pruefe_vertragszeitraum(beginn: date_type, ende: date_type | None) -> None:
    """Regel: Das Startdatum eines Mietvertrags muss vor dessen Enddatum liegen, falls gesetzt."""
    if ende is not None and beginn >= ende:
        raise GeschaeftsregelFehler("Das Startdatum muss vor dem Enddatum liegen.")


def _ueberschneidet(beginn_a: date_type, ende_a, beginn_b: date_type, ende_b) -> bool:
    ende_a = ende_a or MAX_DATE
    ende_b = ende_b or MAX_DATE
    return beginn_a <= ende_b and beginn_b <= ende_a


def pruefe_keine_ueberlappung(
    bestehende_vertraege: Iterable, beginn: date_type, ende, ausgenommen_vertrag_id: int | None = None
) -> None:
    """Regel: Eine Mieteinheit darf im selben Zeitraum nicht durch mehr als einen Mietvertrag
    belegt sein."""
    for vertrag in bestehende_vertraege:
        if ausgenommen_vertrag_id is not None and vertrag.id == ausgenommen_vertrag_id:
            continue
        if _ueberschneidet(beginn, ende, vertrag.beginn, vertrag.ende):
            raise GeschaeftsregelFehler(
                f"Diese Mieteinheit ist im gewählten Zeitraum bereits an {vertrag.mieter.name} vermietet."
            )


def pruefe_immobilie_loeschbar(immobilie) -> None:
    """Regel: Eine Immobilie kann nur gelöscht werden, wenn keine ihrer Mieteinheiten einen
    bestehenden Mietvertrag hat."""
    betroffene_vertraege = sum(len(einheit.mietvertraege) for einheit in immobilie.mieteinheiten)
    if betroffene_vertraege:
        raise GeschaeftsregelFehler(
            "Diese Immobilie hat Mieteinheiten mit bestehenden Mietverträgen und kann nicht gelöscht "
            "werden."
        )


def pruefe_mieteinheit_loeschbar(mieteinheit) -> None:
    """Regel: Eine Mieteinheit kann nur gelöscht werden, wenn kein Mietvertrag auf sie verweist."""
    if mieteinheit.mietvertraege:
        raise GeschaeftsregelFehler(
            "Diese Mieteinheit hat bestehende Mietverträge und kann nicht gelöscht werden."
        )


def pruefe_mieter_loeschbar(mieter) -> None:
    """Regel: Ein Mieter kann nur gelöscht werden, wenn ihm kein Mietvertrag mehr zugeordnet ist."""
    if mieter.mietvertraege:
        raise GeschaeftsregelFehler(
            f"{mieter.name} hat noch {len(mieter.mietvertraege)} Mietvertrag/-verträge und kann nicht "
            "gelöscht werden."
        )


def pruefe_profil_vollstaendig(profil) -> None:
    """Regel: Für den PDF-Export müssen im Vermieterprofil mindestens Name, Straße, PLZ und Ort
    hinterlegt sein."""
    if not profil.ist_vollstaendig():
        raise GeschaeftsregelFehler(
            "Das Vermieterprofil ist unvollständig (Name, Straße, PLZ und Ort werden für den "
            "Briefkopf benötigt)."
        )
