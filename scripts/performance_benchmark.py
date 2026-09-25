"""Performance-Benchmark für Performance und Skalierbarkeit (siehe Anforderungsdokument).

Seedet eine SQLite-Datenbank an der dokumentierten Skalierungsgrenze (20 Mieteinheiten,
200 Mietvertraege, 400 Kostenpositionen) und misst die Antwortzeit der Service-Schicht hinter
den zentralen Bedieninteraktionen. Kein pytest-Test (bewusst nicht unter tests/, damit die
Anzahl der 42 automatisierten Unit-Tests unveraendert bleibt), sondern ein eigenstaendiges,
reproduzierbares Mess-Skript. Aufruf: python scripts/performance_benchmark.py
"""

import statistics
import tempfile
import time
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, select
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
from mietmanager.services.abrechnung import erstelle_abrechnung, lade_abrechnungen

UMLAGE = [Umlageschluessel.FLAECHE, Umlageschluessel.PERSONEN, Umlageschluessel.EINHEITEN]
KOSTENARTEN = [
    "Grundsteuer", "Wasser/Abwasser", "Muellabfuhr", "Hausversicherung",
    "Hausmeister", "Heizung", "Strassenreinigung", "Schornsteinfeger",
]


def seed(session: Session) -> list[Immobilie]:
    mieter_pool = [
        Mieter(anrede=Anrede.FRAU if i % 2 else Anrede.HERR, vorname=f"Vorname{i}", nachname=f"Nachname{i}")
        for i in range(60)
    ]
    session.add_all(mieter_pool)

    immobilien = [
        Immobilie(bezeichnung=f"Immobilie {i}", strasse=f"Strasse {i}", plz="04109", ort="Leipzig")
        for i in range(5)
    ]
    session.add_all(immobilien)

    mieteinheiten = []
    for imm in immobilien:
        for j in range(4):
            me = Mieteinheit(immobilie=imm, bezeichnung=f"Einheit {j}", flaeche_qm=55 + j * 5, zimmeranzahl=2)
            mieteinheiten.append(me)
    session.add_all(mieteinheiten)

    mieter_idx = 0
    for me in mieteinheiten:
        jahr = 2016
        for k in range(10):
            ist_letzter = k == 9
            mv = Mietvertrag(
                mieteinheit=me,
                mieter=mieter_pool[mieter_idx % len(mieter_pool)],
                beginn=date(jahr, 1, 1),
                ende=None if ist_letzter else date(jahr, 12, 31),
                kaltmiete=500 + k * 10,
                nebenkosten_vorauszahlung=150,
                kaution=1500,
                personenzahl=1 + (k % 3),
            )
            session.add(mv)
            mieter_idx += 1
            jahr += 1

    for imm in immobilien:
        for kostenart in KOSTENARTEN:
            for jahr in range(2016, 2026):
                session.add(
                    Kostenposition(
                        immobilie=imm,
                        kostenart=kostenart,
                        betrag=100 + (jahr - 2016) * 5,
                        zeitraum_start=date(jahr, 1, 1),
                        zeitraum_ende=date(jahr, 12, 31),
                        umlageschluessel=UMLAGE[(jahr + len(kostenart)) % 3],
                    )
                )

    session.add(Vermieterprofil(id=1, name="Max Mustermann", strasse="Musterstr. 1", plz="04109", ort="Leipzig"))
    session.commit()
    return immobilien


def messen(label: str, fn, n: int = 30) -> None:
    zeiten = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        zeiten.append((time.perf_counter() - start) * 1000)
    print(
        f"{label:55s} avg={statistics.mean(zeiten):7.2f}ms  "
        f"max={max(zeiten):7.2f}ms  min={min(zeiten):7.2f}ms  (n={n})"
    )


def main() -> None:
    db_path = Path(tempfile.gettempdir()) / "mietmanager_perf_bench.db"
    db_path.unlink(missing_ok=True)

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    session = Session(engine)

    immobilien = seed(session)
    print("Seed: 20 Mieteinheiten, 200 Mietvertraege, 400 Kostenpositionen, 5 Immobilien\n")

    messen("Dashboard-Refresh (alle Kennzahlen)", lambda: (
        session.scalars(select(Immobilie)).all(),
        session.scalars(select(Mieteinheit)).all(),
        [v for v in session.scalars(select(Mietvertrag)).all() if v.ende is None],
    ))
    messen("Mietvertraege-Tab laden (alle 200)", lambda: session.scalars(select(Mietvertrag)).all())
    messen("Kostenpositionen-Tab laden (1 Immobilie, 80)", lambda: session.scalars(
        select(Kostenposition).where(Kostenposition.immobilie_id == immobilien[0].id)
    ).all())
    messen(
        "Abrechnung erstellen (1 Jahr, 4 Vertraege)",
        lambda: erstelle_abrechnung(session, immobilien[0], date(2024, 1, 1), date(2024, 12, 31)),
        n=10,
    )
    messen(
        "Abrechnung erstellen (Worst Case, 10-Jahres-Zeitraum)",
        lambda: erstelle_abrechnung(session, immobilien[1], date(2016, 1, 1), date(2025, 12, 31)),
        n=10,
    )
    messen("Abrechnungsverlauf laden", lambda: lade_abrechnungen(session, immobilien[0].id))

    session.close()
    engine.dispose()
    db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
