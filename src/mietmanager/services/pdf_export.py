"""PDF-Export der Nebenkostenabrechnung als versandfertiger Geschäftsbrief (eine Datei je Mieter)."""

import re
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from mietmanager.models import Abrechnungsposition, Anrede, Mieter, Nebenkostenabrechnung, Vermieterprofil
from mietmanager.services.abrechnung import positionsdetails
from mietmanager.services.regeln import pruefe_profil_vollstaendig


def _dateiname(position: Abrechnungsposition) -> str:
    mieter = position.mietvertrag.mieter
    jahr = position.abrechnung.zeitraum_start.year
    name = f"Nebenkostenabrechnung_{jahr}_{mieter.nachname}_{mieter.vorname}.pdf"
    return re.sub(r"[^\w\-.]", "_", name)


def _anredetext(mieter: Mieter) -> str:
    if mieter.anrede == Anrede.HERR:
        return f"Sehr geehrter Herr {mieter.nachname},"
    if mieter.anrede == Anrede.FRAU:
        return f"Sehr geehrte Frau {mieter.nachname},"
    return "Sehr geehrte Damen und Herren,"


def exportiere_abrechnung(
    abrechnung: Nebenkostenabrechnung, profil: Vermieterprofil, zielordner: Path
) -> list[Path]:
    """Erstellt für jeden Mietvertrag der Abrechnung einen versandfertigen Brief als PDF."""
    pruefe_profil_vollstaendig(profil)
    zielordner.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    absender_style = ParagraphStyle(
        "Absenderzeile", parent=styles["Normal"], fontSize=8, textColor=colors.grey
    )
    datum_style = ParagraphStyle("Datum", parent=styles["Normal"], alignment=TA_RIGHT)
    betreff_style = ParagraphStyle("Betreff", parent=styles["Normal"], fontName="Helvetica-Bold")

    erzeugte_dateien: list[Path] = []

    for position in abrechnung.positionen:
        vertrag = position.mietvertrag
        mieter = vertrag.mieter
        immobilie = abrechnung.immobilie
        pfad = zielordner / _dateiname(position)

        doc = SimpleDocTemplate(
            str(pfad),
            pagesize=A4,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
        )

        elemente = [
            Paragraph(f"{profil.name} · {profil.strasse} · {profil.plz} {profil.ort}", absender_style),
            Spacer(1, 1.2 * cm),
            Paragraph(
                f"{mieter.name}<br/>{immobilie.strasse}<br/>{immobilie.plz} {immobilie.ort}",
                styles["Normal"],
            ),
            Spacer(1, 0.8 * cm),
            Paragraph(f"{profil.ort}, {date.today().strftime('%d.%m.%Y')}", datum_style),
            Spacer(1, 0.8 * cm),
            Paragraph(
                f"Nebenkostenabrechnung {abrechnung.zeitraum_start.strftime('%d.%m.%Y')} – "
                f"{abrechnung.zeitraum_ende.strftime('%d.%m.%Y')}",
                betreff_style,
            ),
            Spacer(1, 0.5 * cm),
            Paragraph(_anredetext(mieter), styles["Normal"]),
            Spacer(1, 0.3 * cm),
            Paragraph(
                f"anbei erhalten Sie die Abrechnung der Nebenkosten für Ihre Mieteinheit "
                f"„{vertrag.mieteinheit.bezeichnung}“ in {immobilie.bezeichnung} für den oben genannten "
                f"Zeitraum.",
                styles["Normal"],
            ),
            Spacer(1, 0.6 * cm),
        ]

        details = positionsdetails(abrechnung, vertrag)
        tabellen_daten = [["Kostenart", "Anteil"]]
        tabellen_daten += [[kostenart, f"{betrag:,.2f} €"] for kostenart, betrag in details]
        tabellen_daten.append(["Gesamtkostenanteil", f"{float(position.anteil_kosten):,.2f} €"])
        tabellen_daten.append(
            ["Geleistete Vorauszahlung", f"{float(position.geleistete_vorauszahlung):,.2f} €"]
        )
        saldo = float(position.saldo)
        saldo_text = "Nachzahlung" if saldo > 0 else "Guthaben"
        tabellen_daten.append([saldo_text, f"{abs(saldo):,.2f} €"])

        tabelle = Table(tabellen_daten, colWidths=[10 * cm, 5 * cm])
        tabelle.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3B4E")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
                    ("LINEABOVE", (0, -3), (-1, -3), 1, colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]
            )
        )
        elemente.append(tabelle)
        elemente.append(Spacer(1, 0.6 * cm))

        if saldo > 0:
            konto_hinweis = f" auf folgendes Konto: {profil.iban}." if profil.iban else "."
            schlusstext = (
                f"Es ergibt sich eine Nachzahlung in Höhe von {saldo:,.2f} €. Wir bitten um Überweisung "
                f"innerhalb von 30 Tagen nach Erhalt dieses Schreibens{konto_hinweis}"
            )
        elif saldo < 0:
            schlusstext = (
                f"Es ergibt sich ein Guthaben in Höhe von {abs(saldo):,.2f} €, das mit der nächsten "
                f"Mietzahlung verrechnet wird."
            )
        else:
            schlusstext = "Es ergibt sich weder eine Nachzahlung noch ein Guthaben."
        elemente.append(Paragraph(schlusstext, styles["Normal"]))
        elemente.append(Spacer(1, 1 * cm))

        elemente.append(Paragraph("Mit freundlichen Grüßen", styles["Normal"]))
        elemente.append(Spacer(1, 1.2 * cm))
        elemente.append(Paragraph(profil.name, styles["Normal"]))

        doc.build(elemente)
        erzeugte_dateien.append(pfad)

    return erzeugte_dateien
