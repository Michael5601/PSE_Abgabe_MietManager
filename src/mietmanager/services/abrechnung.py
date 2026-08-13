"""Berechnung der Nebenkostenabrechnung (Kernprozess der Anwendung).

Vereinfachung/Technical Debt: Vorauszahlungen werden über die volle Anzahl an Monaten
des Abrechnungszeitraums berücksichtigt, unabhängig davon, ob ein Mietvertrag erst
während des Zeitraums begonnen hat. Für unterjährige Mieterwechsel müsste die
Vorauszahlung anteilig pro Monat der tatsächlichen Mietdauer berechnet werden.
"""

from datetime import date

from sqlalchemy.orm import Session

from mietmanager.models import (
    Abrechnungsposition,
    Immobilie,
    Kostenposition,
    Mietvertrag,
    Nebenkostenabrechnung,
    Umlageschluessel,
)


class AbrechnungsFehler(Exception):
    """Wird ausgelöst, wenn eine Nebenkostenabrechnung nicht erstellt werden kann."""


def _aktive_vertraege(immobilie: Immobilie, start: date, ende: date) -> list[Mietvertrag]:
    vertraege = []
    for einheit in immobilie.mieteinheiten:
        for vertrag in einheit.mietvertraege:
            if vertrag.beginn <= ende and (vertrag.ende is None or vertrag.ende >= start):
                vertraege.append(vertrag)
    return vertraege


def _kostenpositionen_im_zeitraum(immobilie: Immobilie, start: date, ende: date) -> list[Kostenposition]:
    return [
        kp for kp in immobilie.kostenpositionen if kp.zeitraum_start <= ende and kp.zeitraum_ende >= start
    ]


def _umlage_gewicht(vertrag: Mietvertrag, schluessel: Umlageschluessel) -> float:
    if schluessel == Umlageschluessel.FLAECHE:
        return float(vertrag.mieteinheit.flaeche_qm)
    if schluessel == Umlageschluessel.PERSONEN:
        return float(vertrag.personenzahl)
    if schluessel == Umlageschluessel.EINHEITEN:
        return 1.0
    raise AbrechnungsFehler(f"Unbekannter Umlageschlüssel: {schluessel}")


def erstelle_abrechnung(
    session: Session, immobilie: Immobilie, start: date, ende: date
) -> Nebenkostenabrechnung:
    """Erstellt und persistiert eine Nebenkostenabrechnung für eine Immobilie und einen Zeitraum."""
    if start >= ende:
        raise AbrechnungsFehler("Das Startdatum muss vor dem Enddatum liegen.")

    kostenpositionen = _kostenpositionen_im_zeitraum(immobilie, start, ende)
    if not kostenpositionen:
        raise AbrechnungsFehler("Für den gewählten Zeitraum sind keine Kostenpositionen erfasst.")

    vertraege = _aktive_vertraege(immobilie, start, ende)
    if not vertraege:
        raise AbrechnungsFehler("Für den gewählten Zeitraum gibt es keine aktiven Mietverträge.")

    kosten_je_vertrag: dict[int, float] = {v.id: 0.0 for v in vertraege}

    for kp in kostenpositionen:
        gewichte = {v.id: _umlage_gewicht(v, kp.umlageschluessel) for v in vertraege}
        gesamtgewicht = sum(gewichte.values())
        if gesamtgewicht == 0:
            raise AbrechnungsFehler(
                f"Kostenposition '{kp.kostenart}' kann nicht verteilt werden (Gesamtgewicht 0)."
            )
        for v in vertraege:
            kosten_je_vertrag[v.id] += float(kp.betrag) * gewichte[v.id] / gesamtgewicht

    monate = (ende.year - start.year) * 12 + (ende.month - start.month) + 1

    abrechnung = Nebenkostenabrechnung(immobilie=immobilie, zeitraum_start=start, zeitraum_ende=ende)

    for v in vertraege:
        vorauszahlung = round(float(v.nebenkosten_vorauszahlung) * monate, 2)
        anteil = round(kosten_je_vertrag[v.id], 2)
        abrechnung.positionen.append(
            Abrechnungsposition(
                mietvertrag=v,
                anteil_kosten=anteil,
                geleistete_vorauszahlung=vorauszahlung,
                saldo=round(anteil - vorauszahlung, 2),
            )
        )

    session.add(abrechnung)
    session.commit()
    return abrechnung


def positionsdetails(
    abrechnung: Nebenkostenabrechnung, mietvertrag: Mietvertrag
) -> list[tuple[str, float]]:
    """Rekonstruiert die Kostenanteile je Kostenart für einen Mietvertrag (für die PDF-Ausgabe).

    Wird nicht in der Datenbank gespeichert, sondern aus den Kostenpositionen neu berechnet,
    um keine redundante Line-Item-Tabelle pflegen zu müssen.
    """
    kostenpositionen = _kostenpositionen_im_zeitraum(
        abrechnung.immobilie, abrechnung.zeitraum_start, abrechnung.zeitraum_ende
    )
    vertraege = _aktive_vertraege(abrechnung.immobilie, abrechnung.zeitraum_start, abrechnung.zeitraum_ende)

    details = []
    for kp in kostenpositionen:
        gewichte = {v.id: _umlage_gewicht(v, kp.umlageschluessel) for v in vertraege}
        gesamtgewicht = sum(gewichte.values())
        anteil = float(kp.betrag) * gewichte.get(mietvertrag.id, 0.0) / gesamtgewicht if gesamtgewicht else 0.0
        details.append((kp.kostenart, round(anteil, 2)))
    return details
