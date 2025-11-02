# THWS Vorlesungsplan MCP-Server

Ein Model Context Protocol (MCP) Server, der LLMs direkten Zugriff auf die Vorlesungspläne der THWS Business-Fakultät ermöglicht.

## Was macht dieser Server?

Dieser MCP-Server scrapt automatisch die Vorlesungspläne von der THWS Business-Website und stellt sie LLMs über standardisierte Tools und Resources zur Verfügung. LLMs können damit:

- Verfügbare Studiengänge und Semester abfragen
- Vorlesungspläne für bestimmte Studiengänge und Semester abrufen
- Zeitlich gefilterte Vorlesungen anzeigen (z.B. "Was steht nächste Woche an?")

## Unterstützte Studiengänge

Der Server unterstützt alle auf https://business.thws.de/studierende/vorlesungs-und-belegungsplaene/ verfügbaren Studiengänge:

- Bachelor Betriebswirtschaft (BBW)
- Bachelor Business Analytics (BBA)
- Bachelor Digitales Rettungsmanagement (BRMD)
- Bachelor International Management (BIM)
- Bachelor Kulinarik- und Weintourismus (BKWD)
- Bachelor Medienmanagement (BMM)
- Master Integriertes Innovationsmanagement (M2IV)
- Master Managing Global Dynamics (MGD)
- Master Marken- und Medienmanagement (MMM)

## Installation

### Voraussetzungen

- Python 3.10 oder höher
- pip Package Manager

### Dependencies installieren

Um alle Abhängikeiten zu installieren, bitte folgenden Befehl im thws-scheudler Verzeichnis ausführen. Es wird empfohlen, das mit einer virtuellen Umgebung zu machen.

```bash
pip install -e .
```

## Verwendung

### Als MCP-Server starten

```bash
python business-thws-lecture.py
```

Der Server läuft dann im MCP-Modus und kann von kompatiblen LLM-Clients (z.B. Claude Desktop) verwendet werden.

### Test-Modus

Zum Testen der Funktionalität ohne MCP-Client:

```bash
python business-thws-lecture.py test
```

Dies führt zwei Tests aus:
1. Lädt alle verfügbaren Studiengänge und Semester
2. Holt exemplarisch den Vorlesungsplan für BBA Semester 7

## MCP-Konfiguration

### Claude Desktop Integration

Füge folgenden Eintrag in deine Claude Desktop Config hinzu (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "thws-lecture": {
      "command": "<PFAD>/uv.exe",
      "args": [
        "--directory",
        "<PFAD>/WIDB2-mcp/thws-lecture",
        "run",
        "business-thws-lecture.py"
      ]
    }
  }
}
```

**Wichtig:** Ersetze `<PFAD>` mit deinem absoluten Pfad.

**uv-Pfad finden:**
```bash
# Windows (PowerShell)
where.exe uv

# Linux/macOS
which uv
```

**Config-Datei öffnen:**  
Claude Desktop → Profil → Einstellungen → Entwickler → Config bearbeiten

### Andere MCP-Clients

Der Server ist kompatibel mit jedem MCP-Client, der das MCP-Protokoll implementiert. Konfiguration analog zur Claude Desktop Integration.

## Funktionsweise

### Architektur

Der Server basiert auf FastMCP und bietet:

1. **Resource (`schedule://available`)**: Statische Liste aller verfügbaren Studiengänge und Semester
2. **Tool (`get_schedule`)**: Dynamisches Abrufen von Vorlesungen mit Zeitfilterung

### Datenfluss

```
LLM Request
    ↓
MCP-Server (business-thws-lecture.py)
    ↓
Web Scraping (BeautifulSoup)
    ↓
HTML-Parsing & Datenextraktion
    ↓
Zeitfilterung & Formatierung
    ↓
Strukturierte Antwort an LLM
```

### Scraping-Logik

Der Server:
1. Lädt die Übersichtsseite der THWS Business-Fakultät
2. Parst alle Accordion-Elemente (Studiengänge)
3. Extrahiert Semester-Tabellen und URLs zu HTML-Vorlesungsplänen
4. Bei Tool-Aufruf: Lädt und parst den konkreten Vorlesungsplan
5. Filtert nach angefragetem Zeitraum
6. Formatiert die Daten strukturiert für das LLM

## API-Dokumentation

### Resource: `schedule://available`

**Beschreibung:** Liste aller verfügbaren Studiengänge und Semester

**Rückgabe:** Textbasierte Übersicht aller scrapbaren Vorlesungspläne

**Beispiel-Output:**
```
VERFÜGBARE VORLESUNGSPLÄNE
================================================================================

Bachelor Business Analytics (BBA):
  - Semester 7 - Wintersemester (WS) 25/26
  
Bachelor Betriebswirtschaft (BBW):
  - Semester 1 - Wintersemester (WS) 25/26
  - Semester 3 - Wintersemester (WS) 25/26
  ...
```

### Tool: `get_schedule`

**Beschreibung:** Holt Vorlesungen für einen Studiengang/Semester über mehrere Tage

**Parameter:**
- `course` (string, required): Studiengang-Abkürzung (z.B. "BBA", "BBW", "BAMD")
- `semester` (string, required): Semester als Zahl (z.B. "1", "3", "5", "7")
- `days` (integer, optional): Anzahl Tage ab heute (default: 7, 0 = nur heute)

**Rückgabe:** Formatierter Vorlesungsplan mit:
- Studiengangs-Info
- Semester-Info
- Zeitraum
- Vorlesungen sortiert nach Datum/Zeit mit:
    - Datum und Wochentag
    - Uhrzeit (Start/Ende)
    - Fach und Titel
    - Typ (Vorlesung/Übung)
    - Dozent
    - Raum
    - Hinweise (falls vorhanden)

**Beispiel-Aufruf:**
```python
get_schedule(course="BBA", semester="7", days=14)
```

**Beispiel-Output:**
```
VORLESUNGSPLAN
Studiengang: Bachelor Business Analytics (BBA)
Semester: 7 
Semester-Info: Wintersemester (WS) 25/26
Zeitraum: 2025-11-02 bis 2025-11-16
Gefunden: 15 Vorlesungen

################################################################################
# Mo, 2025-11-04
################################################################################

================================================================================
Datum: Mo, 2025-11-04
Zeit: 08:00 - 09:30 Uhr
Fach: Data Science
Titel: Machine Learning Basics
Typ: Vorlesung
Dozent: Prof. Dr. Müller
Raum: I.1.12
================================================================================
...
```

## Technische Details

### Web-Scraping

- **Ziel-URL:** https://business.thws.de/studierende/vorlesungs-und-belegungsplaene/
- **HTML-Parser:** BeautifulSoup4
- **Scraping-Elemente:**
    - Accordion-Struktur für Studiengänge
    - Tabellen für Semester-Zuordnung
    - HTML-Vorlesungspläne mit komplexer Tabellenstruktur

### Datenextraktion

Der Parser extrahiert aus HTML-Tabellen:
- Studienwochen
- Tage (Datum, Wochentag)
- Vorlesungen mit Rowspan/Colspan-Handling
- Zeitslots (Start-/Endzeit)
- Metadaten (Fach, Titel, Typ, Dozent, Raum, Hinweise)

### Zeitfilterung

- Basisdatum: Aktuelles Datum beim Aufruf
- Filterung: `heute <= Vorlesungsdatum <= heute + days`
- Sortierung: Chronologisch nach Datum und Uhrzeit

## Einschränkungen

- **Nur HTML-basierte Pläne:** PDF-Pläne werden nicht unterstützt
- **Abhängig von HTML-Struktur:** Änderungen am Website-Layout können den Parser brechen
- **Keine Authentifizierung:** Nur öffentlich zugängliche Pläne
- **Statisches Scraping:** Keine Echtzeit-Updates (Daten werden bei jedem Aufruf neu geladen)

## Fehlerbehandlung

Der Server fängt folgende Fehler ab:
- HTTP-Fehler beim Laden der Website
- Parse-Fehler bei ungültiger HTML-Struktur
- Ungültige Studiengänge/Semester
- Fehlende Vorlesungspläne im angegebenen Zeitraum

Fehler werden mit aussagekräftigen Meldungen an das LLM zurückgegeben.

## Projektkontext

Dieser MCP-Server ist Teil einer Präsentation über das Model Context Protocol im Schwerpunkt WIDB2 im Teilbereich von Prof. Robert Butscher.

## Weiterführende Links

- [MCP Dokumentation](https://modelcontextprotocol.io/docs/)
- [Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [THWS Business](https://business.thws.de/)