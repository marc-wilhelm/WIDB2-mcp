# Python SDK von Model Context Protocol (MCP)

<div align="center">

[![Python Version][python-badge]][python-url]

</div>

[python-badge]: https://img.shields.io/badge/Python-3.13-blue
[python-url]: https://www.python.org/downloads/

<!-- omit in toc -->
## Inhaltsverzeichnis

- [Installation](#installation)
  - [Voraussetzungen](#voraussetzungen)
  - [Projekt erstellen](#projekt-erstellen)
  - [MCP hinzufügen](#mcp-hinzufügen)

## Installation

> **Quelle:** [Offizielle Anleitung](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file) des Python SDK von MCP

### Voraussetzungen

- Eine funktionsfähige Python-Installation (Version 3.13 oder höher empfohlen)
- Zunächst ist die Installation von [**uv**](https://docs.astral.sh/uv/) empfohlen. Das ist ein moderner Python-Paketmanager, der eine einfache und effiziente 
Verwaltung von Paketen ermöglicht (ähnlich wie pip, aber mit erweiterten Funktionen).

### Projekt erstellen

Nach der Installation von uv kann man das Projekt mit folgendem Befehl erstellen:

```bash
uv init
```

Alternativ kann man das Proejekt auch in einem Unterordner erstellen (z.B. mcp-server-demo). Allerdings muss anschließend auch in das Verzeichnis 
gewechselt werden.

```bash
uv init mcp-server-demo

cd mcp-server-demo
```

### MCP hinzufügen

MCP zu den Projektabhängigkeiten hinzufügen. Dieser Befehl erstellt automatisch eine virtuelle Python-Umgebung und installiert alle notwendigen Abhängigkeiten:

```bash
uv add "mcp[cli]"
```
