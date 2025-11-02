from mcp.server.fastmcp import FastMCP
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import unquote

mcp = FastMCP("THWS Scheduler")

# Basis-URL für die Vorlesungsplan-Übersicht
BASE_URL = "https://business.thws.de/studierende/vorlesungs-und-belegungsplaene/"

def get_available_schedules():
    """
    Scraped die Übersichtsseite und gibt alle verfügbaren Vorlesungspläne zurück

    Returns:
        Dict mit Studiengängen -> Semester -> URLs
        Beispiel: {"BBA": {"7": [{"url": "...", "semester_info": "WS 25/26", "studiengang_name": "Bachelor Business Analytics"}]}}
    """
    try:
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            print(f"Fehler beim Abrufen der Seite: Status {response.status_code}")
            return {}

        soup = BeautifulSoup(response.content, "html.parser")
        schedules = {}

        # Alle Accordion-Elemente finden (jedes repräsentiert einen Studiengang)
        accordions = soup.find_all("div", class_="accordion")

        if not accordions:
            print("Keine Accordion-Elemente gefunden. Prüfe HTML-Struktur.")
            return {}

        for accordion in accordions:
            # Studiengangsname und Abkürzung aus Überschrift extrahieren
            heading = accordion.find(["h2", "h3"])
            if not heading:
                continue

            # Text von "Bachelor Betriebswirtschaft (BBW)" extrahieren
            heading_text = heading.text.strip()

            # Regulärer Ausdruck, um Studiengangsname und Abkürzung zu extrahieren
            match = re.search(r"(Bachelor|Master)\s+([^(]+)\s*\(([^)]+)\)", heading_text)
            if not match:
                continue

            studiengang_typ = match.group(1)  # Bachelor oder Master
            studiengang_name = match.group(2).strip()  # z.B. "Betriebswirtschaft"
            studiengang_abk = match.group(3).strip()  # z.B. "BBW", "BBA"
            studiengang_vollname = f"{studiengang_typ} {studiengang_name}"  # "Bachelor Betriebswirtschaft"

            # Suche nach der Semester-Tabelle innerhalb des Accordions
            tabellen = accordion.find_all("table")

            for tabelle in tabellen:
                # Vorlesungspläne in der Tabelle finden
                rows = tabelle.find_all("tr")[1:]  # Erste Zeile überspringen (Header)

                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue

                    # Semestername aus erster Zelle
                    semester_cell = cells[0].text.strip()

                    # Links aus zweiter Zelle
                    links = cells[1].find_all("a")

                    # Extrahiere alle Semesterzahlen aus dem Zelltext
                    # Beispiel: "6./7. Semester" -> ["6", "7"]
                    semester_zahlen = re.findall(r"(\d+)\.", semester_cell)

                    if not semester_zahlen:
                        continue

                    for link in links:
                        href = link.get("href")
                        if href and ".html" in href:
                            # Relativen Link in absoluten umwandeln
                            if not href.startswith("http"):
                                if href.startswith("/"):
                                    full_url = f"https://business.thws.de{href}"
                                else:
                                    full_url = f"https://business.thws.de/{href}"
                            else:
                                full_url = href

                            # Semester-Info aus Dateinamen extrahieren
                            # URL-decode den Dateinamen (z.B. BBA%207%20WS%2025_26.html -> BBA 7 WS 25_26.html)
                            filename = unquote(href.split("/")[-1])
                            semester_info_match = re.search(r'(WS|SS)\s+(\d{2})_(\d{2})', filename)
                            semester_info_short = "Unbekannt"
                            semester_info_long = "Unbekannt"
                            if semester_info_match:
                                semester_type = semester_info_match.group(1)
                                year = f"{semester_info_match.group(2)}/{semester_info_match.group(3)}"
                                semester_info_short = f"{semester_type} {year}"
                                # Erweiterte Ausgabe: "Wintersemester (WS) 25/26"
                                semester_type_long = "Wintersemester" if semester_type == "WS" else "Sommersemester"
                                semester_info_long = f"{semester_type_long} ({semester_type}) {year}"

                            # Gruppennamen extrahieren (falls vorhanden)
                            link_text = link.text.strip()
                            gruppe_match = re.search(r"Gr\.\s*([A-D])", link_text)
                            gruppe = gruppe_match.group(1) if gruppe_match else None

                            # Für jede gefundene Semesterzahl einen Eintrag erstellen
                            # Beispiel: "6./7. Semester" -> Beide Semester 6 und 7 bekommen denselben Link
                            for semester_zahl in semester_zahlen:
                                if studiengang_abk not in schedules:
                                    schedules[studiengang_abk] = {}
                                if semester_zahl not in schedules[studiengang_abk]:
                                    schedules[studiengang_abk][semester_zahl] = []

                                schedules[studiengang_abk][semester_zahl].append({
                                    "url": full_url,
                                    "semester_info": semester_info_long,
                                    "semester_info_short": semester_info_short,
                                    "gruppe": gruppe,
                                    "studiengang_name": studiengang_vollname
                                })

        return schedules
    except Exception as e:
        print(f"Fehler beim Laden der Übersichtsseite: {e}")
        import traceback
        traceback.print_exc()
        return {}

def parse_week(table):
    """
    Parst eine Woche aus einem Vorlesungsplan (HTML-Tabelle)

    Args:
        table: BeautifulSoup table element

    Returns:
        Dict mit Wochennummer und Tagen mit Vorlesungen
    """
    # Studienwoche extrahieren - suche rückwärts nach dem vorherigen div.w2
    studienwoche_text = "Unbekannt"
    header_div = table.find_previous_sibling("div", class_="w2")
    if header_div:
        studienwoche_text = header_div.text.strip()

    if not table:
        return {"studienwoche": studienwoche_text, "tage": []}

    rows = table.find_all("tr")
    if len(rows) < 2:
        return {"studienwoche": studienwoche_text, "tage": []}

    # Header-Zeile parsen - nur Zellen mit class="t" sind Tage
    day_spans = []

    # Tracke die Spalten-Position für jede Tag-Zelle
    col_position = 0
    all_cells = rows[0].find_all("td")

    for cell_idx, td in enumerate(all_cells):
        colspan = int(td.get("colspan", 1))

        if "t" in td.get("class", []):
            text = td.get_text(strip=True)

            # Datum extrahieren - Format: "Mo, 27.10.25" (mit Komma!)
            date_match = re.search(r'(\w+),\s*(\d{2})\.(\d{2})\.(\d{2})', text)
            if date_match:
                wochentag = date_match.group(1)
                day = date_match.group(2)
                month = date_match.group(3)
                year = f"20{date_match.group(4)}"
                datum_lang = f"{year}-{month}-{day}"

                day_spans.append({
                    "wochentag": wochentag,
                    "datum_kurz": f"{day}.{month}.{year[2:]}",
                    "datum_lang": datum_lang,
                    "start_col": col_position,
                    "end_col": col_position + colspan,
                    "vorlesungen": []
                })

        col_position += colspan

    # Vorlesungen parsen
    active_spans = {}

    for row_num, row in enumerate(rows[1:], start=1):
        cells = row.find_all("td")
        if not cells:
            continue

        col = 0

        for cell_idx, td in enumerate(cells):
            # Rowspan-Verwaltung
            while col in active_spans:
                if active_spans[col] > 1:
                    active_spans[col] -= 1
                else:
                    del active_spans[col]
                col += 1

            colspan = int(td.get("colspan", 1))
            rowspan = int(td.get("rowspan", 1))
            classes = td.get("class", [])

            # Vorlesungszelle?
            if "v" in classes:
                lecture_id = td.get("id", "")

                # Finde zugehörigen Tag
                target = None
                for day in day_spans:
                    if day["start_col"] <= col < day["end_col"]:
                        target = day
                        break

                if target:
                    # Text parsen
                    text = unescape(td.decode_contents().replace("<br/>", "\n")).strip()
                    lines = [l.strip() for l in text.split("\n") if l.strip()]

                    vorl = {
                        "id": lecture_id,
                        "hinweis": None,
                        "startzeit": None,
                        "endzeit": None,
                        "fach": None,
                        "titel": None,
                        "typ": None,
                        "dozent": None,
                        "raum": None
                    }

                    # Zeit finden
                    zeit_re = re.compile(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})')

                    for i, line in enumerate(lines):
                        m = zeit_re.search(line)
                        if m:
                            vorl["startzeit"] = m.group(1)
                            vorl["endzeit"] = m.group(2)

                            if i > 0:
                                vorl["hinweis"] = " / ".join(lines[:i])

                            rest = lines[i+1:]
                            if len(rest) >= 5:
                                vorl["fach"] = rest[0]
                                vorl["titel"] = rest[1]
                                vorl["typ"] = rest[2]
                                vorl["dozent"] = rest[3]
                                vorl["raum"] = rest[4]
                            break

                    if vorl["startzeit"] and vorl["endzeit"] and vorl["fach"]:
                        clean_vorl = {k: v for k, v in vorl.items() if v is not None}
                        target["vorlesungen"].append(clean_vorl)

            # Rowspan merken
            if rowspan > 1:
                for c in range(col, col + colspan):
                    active_spans[c] = rowspan - 1

            col += colspan

    return {
        "studienwoche": studienwoche_text,
        "tage": day_spans
    }

def fetch_schedule_from_url(url):
    """
    Lädt einen Vorlesungsplan von einer URL und parst alle Wochen
    KORRIGIERTE VERSION

    Returns:
        Liste von Tagen mit Vorlesungen
    """
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.content, "html.parser")

        # Parse alle Wochen (jedes div.w2 mit nachfolgender Tabelle)
        all_days = []
        for week_div in soup.find_all("div", class_="w2"):
            table = week_div.find_next_sibling("table")
            if table:
                week_data = parse_week(table)
                all_days.extend(week_data["tage"])

        return all_days
    except Exception as e:
        print(f"Fehler beim Laden des Vorlesungsplans: {e}")
        import traceback
        traceback.print_exc()
        return []

def format_lecture(lecture, datum, wochentag):
    """Formatiert eine einzelne Vorlesung für die Ausgabe"""
    output = f"""
{'='*80}
Datum: {wochentag}, {datum}
Zeit: {lecture['startzeit']} - {lecture['endzeit']} Uhr
Fach: {lecture['fach']}
Titel: {lecture['titel']}
Typ: {lecture['typ']}
Dozent: {lecture['dozent']}
Raum: {lecture['raum']}
"""
    if lecture.get('hinweis'):
        output += f"Hinweis: {lecture['hinweis']}\n"

    output += "=" * 80 + "\n"
    return output

# ============= RESOURCES =============

@mcp.resource("schedule://available")
def get_available_courses() -> str:
    """Resource: Liste aller verfügbaren Studiengänge und Semester"""
    schedules = get_available_schedules()

    if not schedules:
        return "Keine Vorlesungspläne gefunden."

    result = "VERFÜGBARE VORLESUNGSPLÄNE\n"
    result += "=" * 80 + "\n\n"

    for studiengang in sorted(schedules.keys()):
        # Hole den vollen Namen aus dem ersten Semester
        first_semester = list(schedules[studiengang].keys())[0]
        studiengang_vollname = schedules[studiengang][first_semester][0]["studiengang_name"]

        result += f"\n{studiengang_vollname} ({studiengang}):\n"
        for semester in sorted(schedules[studiengang].keys(), key=int):
            semester_info = schedules[studiengang][semester][0]["semester_info"]
            result += f"  - Semester {semester} - {semester_info}\n"

    return result

# ============= TOOLS =============

@mcp.tool()
def get_schedule(course: str, semester: str, days: int = 7) -> str:
    """
    Tool: Holt Vorlesungen für einen Studiengang/Semester über mehrere Tage

    Args:
        course: Studiengang (z.B. "BBA", "BBW", "BAMD")
        semester: Semester als Zahl (z.B. "1", "3", "5", "7")
        days: Anzahl Tage ab heute (default: 7, 0 = nur heute)
    """
    # Hole verfügbare Pläne
    schedules = get_available_schedules()

    course_upper = course.upper()

    # Prüfe ob Studiengang existiert
    if course_upper not in schedules:
        available = ", ".join(sorted(schedules.keys()))
        return f"Studiengang '{course}' nicht gefunden.\nVerfügbare Studiengänge: {available}"

    # Prüfe ob Semester existiert
    if semester not in schedules[course_upper]:
        available = ", ".join(sorted(schedules[course_upper].keys()))
        return f"Semester {semester} für {course} nicht gefunden.\nVerfügbare Semester: {available}"

    # Hole URL des Vorlesungsplans
    plan_info = schedules[course_upper][semester][0]
    url = plan_info["url"]
    semester_info = plan_info["semester_info"]
    studiengang_name = plan_info["studiengang_name"]

    # Lade und parse den Vorlesungsplan
    all_days = fetch_schedule_from_url(url)

    if not all_days:
        return f"Konnte Vorlesungsplan nicht laden: {url}"

    # Filtere nach Zeitraum
    now = datetime.now()
    end_date = now + timedelta(days=days)

    filtered_lectures = []
    for day in all_days:
        try:
            # Parse Datum (Format: "YYYY-MM-DD")
            day_date = datetime.strptime(day["datum_lang"], "%Y-%m-%d")

            # Prüfe Zeitraum
            if now.date() <= day_date.date() <= end_date.date():
                for lecture in day["vorlesungen"]:
                    filtered_lectures.append({
                        "datum": day["datum_lang"],
                        "wochentag": day["wochentag"],
                        "lecture": lecture
                    })
        except Exception as e:
            print(f"Fehler beim Parsen des Datums: {e}")
            continue

    if not filtered_lectures:
        return f"Keine Vorlesungen gefunden für {course} Semester {semester} in den nächsten {days} Tagen."

    # Sortiere nach Datum und Zeit
    filtered_lectures.sort(key=lambda x: (x["datum"], x["lecture"]["startzeit"]))

    # Formatiere Ausgabe
    result = f"""VORLESUNGSPLAN
Studiengang: {studiengang_name} ({course_upper})
Semester: {semester} 
Semester-Info: {semester_info}
Zeitraum: {now.strftime('%Y-%m-%d')} bis {end_date.strftime('%Y-%m-%d')}
Gefunden: {len(filtered_lectures)} Vorlesungen

"""

    current_date = None
    for item in filtered_lectures:
        # Datum-Header wenn sich Datum ändert
        if item["datum"] != current_date:
            current_date = item["datum"]
            result += f"\n{'#'*80}\n"
            result += f"# {item['wochentag']}, {item['datum']}\n"
            result += f"{'#'*80}\n"

        result += format_lecture(item["lecture"], item["datum"], item["wochentag"])

    return result

if __name__ == "__main__":
    import sys

    # Test-Modus: python business-thws-lecture.py test
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("\n" + "="*80)
        print("TEST-MODUS - THWS Scheduler")
        print("="*80 + "\n")

        # Test 1: Verfügbare Pläne
        print("📋 Test 1: Verfügbare Studiengänge/Semester laden...\n")
        print(get_available_courses())

        # Test 2: Vorlesungsplan abrufen
        print("\n" + "="*80)
        print("📅 Test 2: Vorlesungsplan für BBA Semester 7 (nächste 7 Tage)...\n")
        result = get_schedule(course="BBA", semester="7", days=7)
        print(result)

        print("\n✅ Tests abgeschlossen!")
    else:
        # Normaler MCP-Server-Modus
        mcp.run()