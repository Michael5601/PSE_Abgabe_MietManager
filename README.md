# MietManager
Desktop-Anwendung zur Verwaltung von Mietobjekten, Mietverträgen und Nebenkostenabrechnungen für private Kleinvermieter.

Portfolioprojekt im Kurs *Projekt: Software Engineering (DLMCSPSE01_D)* an der IU Internationale Hochschule.

## Customer Value
Private Vermieter mit wenigen Wohneinheiten verwalten Mietverträge und Nebenkosten heute meist in Excel oder auf Papier. MietManager bündelt das in einer Desktop-App mit automatischer Nebenkostenabrechnung nach Umlageschlüssel (Fläche/Personen/Einheiten)
als zentralem Mehrwert gegenüber einer einfachen Tabellenkalkulation.

## Projektstruktur
```
src/mietmanager/        Quellcode der Anwendung
  models/               Datenmodell (Geschäftsobjekte)
  services/             Geschäftslogik (Geschäftsregeln, Abrechnungsberechnung, PDF-Export)
  ui/                   PyQt6-GUI (Fenster, Tabs, Dialoge)
  data/                 Datenzugriff, Testdaten-Seed
tests/                  Unit-Tests
```

## Setup & Ausführung
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
mietmanager
```

Das Projekt ist als installierbares Python-Modul (`pyproject.toml`, setuptools-Backend) aufgesetzt.
`pip install -e ".[dev]"` installiert die Anwendung im editierbaren Modus inkl. Test-/Build-Abhängigkeiten
und registriert den Kommandozeilenbefehl `mietmanager` (GUI-Entry-Point, siehe `[project.gui-scripts]`).
Für die finale Auslieferung wird zusätzlich eine eigenständige Windows-.exe per PyInstaller gebaut, damit die Anwendung auch ohne manuelle `pip`-Installation lauffähig ist.

## Tests
```bash
pytest
```
