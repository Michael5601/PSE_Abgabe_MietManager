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
scripts/                Performance-Benchmark (siehe Testdokument)
docs/                   Projektdokumentation, Anforderungsdokument, Spezifikationsdokument,
                         Architekturdokument, Testdokument und Abstract als PDF
abgabe/                 Abgabe-PDFs aus Phase 1 und Phase 2 sowie Abstract und Finales Produkt
                         aus Phase 3
```
