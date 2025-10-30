# KIGate Agenten - Entwickler- und Anwenderdokumentation

Diese Dokumentation erklärt, wie Sie Agenten in KIGate verwenden und erstellen können. Agenten sind die Kernkomponenten des Systems, die spezifische KI-basierte Aufgaben ausführen.

> 🚀 **Neu hier?** Beginnen Sie mit dem [**Schnellstart Guide**](QUICK_START_AGENTS.md) für einen 5-Minuten-Einstieg!

## Inhaltsverzeichnis

1. [Was sind Agenten?](#was-sind-agenten)
2. [Agent-Architektur](#agent-architektur)
3. [YAML-Dateistruktur](#yaml-dateistruktur)
4. [Verwaltung über das Admin Panel](#verwaltung-über-das-admin-panel)
5. [Beispiel-Agenten](#beispiel-agenten)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Was sind Agenten?

Agenten in KIGate sind konfigurierbare KI-Einheiten, die spezifische Aufgaben ausführen. Jeder Agent wird durch eine YAML-Datei definiert und kann über das Admin Panel verwaltet werden. Agenten können für verschiedene Zwecke eingesetzt werden:

- **Textverarbeitung**: Übersetzung, Optimierung, Korrektur
- **Inhaltsbewertung**: Prüfung von Essays, Dokumenten
- **Datenanalyse**: Auswertung und Interpretation von Daten
- **Automatisierung**: Wiederkehrende KI-Aufgaben

## Agent-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    KIGate Agent System                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ Admin Panel  │───►│ Agent Service   │───►│ YAML Files  │ │
│  │              │    │                 │    │ /agents/    │ │
│  │ Web Interface│    │ - Create/Update │    │ *.yml       │ │
│  │ - Create     │    │ - Validate      │    │             │ │
│  │ - Edit       │    │ - Parse YAML    │    │             │ │
│  │ - Delete     │    │ - File handling │    │             │ │
│  │ - Clone      │    │                 │    │             │ │
│  └──────────────┘    └─────────────────┘    └─────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Agent YAML Structure                     │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ name: "agent-identifier"                                │ │
│  │ description: "What the agent does"                      │ │
│  │ role: "System prompt/persona"                           │ │
│  │ provider: "openai" | "claude" | etc.                   │ │
│  │ model: "gpt-4" | "gpt-3.5-turbo" | etc.               │ │
│  │ task: |                                                 │ │
│  │   Detailed instructions for the agent                   │ │
│  │   - What to do                                          │ │
│  │   - How to respond                                      │ │
│  │   - Output format                                       │ │
│  │ parameters:                                             │ │
│  │   - ParameterName:                                      │ │
│  │       type: string|number|boolean                       │ │
│  │       description: "What this parameter does"          │ │
│  │       default: "optional default value"                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Agent Workflow                       │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  1. User creates agent via Admin Panel or YAML file    │ │
│  │  2. AgentService validates YAML structure              │ │
│  │  3. Agent stored as .yml file in /agents/ directory    │ │
│  │  4. Agent becomes available for API calls              │ │
│  │  5. Parameters can customize agent behavior             │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## YAML-Dateistruktur

Jeder Agent wird durch eine YAML-Datei im `agents/` Verzeichnis definiert. Die Datei muss folgende Struktur haben:

### Pflichtfelder

```yaml
name: agent-name
description: "Kurze Beschreibung des Agenten"
role: "Die Rolle des Agenten (System-Prompt)"
provider: openai  # oder andere Provider
model: gpt-4      # Spezifisches Modell
task: |
  Detaillierte Aufgabenbeschreibung für den Agenten.
  Hier werden die spezifischen Anweisungen definiert.
```

### Optionale Felder

```yaml
parameters:
  - ParameterName:
      type: string
      description: "Beschreibung des Parameters"
      default: "Standard-Wert (optional)"
  - AnotherParameter:
      type: number
      description: "Numerischer Parameter"
```

### Felddetails

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `name` | String | ✅ | Eindeutiger Name (1-100 Zeichen, wird als Dateiname verwendet) |
| `description` | String | ✅ | Kurze Beschreibung (1-500 Zeichen) |
| `role` | String | ✅ | System-Prompt/Rolle des Agenten (1-200 Zeichen) |
| `provider` | String | ✅ | KI-Provider (z.B. "openai", "claude") (1-50 Zeichen) |
| `model` | String | ✅ | Spezifisches Modell (z.B. "gpt-4", "gpt-3.5-turbo") (1-100 Zeichen) |
| `task` | String | ✅ | Detaillierte Aufgabenbeschreibung (unbegrenzt) |
| `parameters` | Array | ❌ | Liste von Parametern für den Agenten |

### Parameter-Definition

Parameter ermöglichen es, Agenten flexibel zu konfigurieren:

```yaml
parameters:
  - Inputtext:
      type: string
      description: "Der zu verarbeitende Text"
  - Language:
      type: string  
      description: "Zielsprache für Übersetzung"
      default: "deutsch"
  - Temperature:
      type: number
      description: "Kreativität des Modells (0.0-1.0)"
      default: 0.7
```

**Unterstützte Parameter-Typen:**
- `string`: Textparameter
- `number`: Numerische Werte
- `boolean`: Wahr/Falsch-Werte

### Parameter-Verwendung über das `/agent/execute` API

Parameter können über das REST-API zur Laufzeit übertragen werden, um das Agent-Verhalten anzupassen:

#### API-Request mit Parametern

```json
{
    "agent_name": "translation-agent",
    "provider": "openai",
    "model": "gpt-4",
    "message": "Hello, how are you today?",
    "user_id": "user-123-456",
    "parameters": {
        "language": "French"
    }
}
```

#### Verarbeitung der Parameter

1. **Parameter-Integration**: Die API kombiniert die Parameter automatisch mit der Agent-Aufgabe
2. **Kontext-Erweiterung**: Parameter werden als zusätzlicher Kontext zur Aufgabe hinzugefügt
3. **Format**: Parameter werden als `key: value` Paare in den Task-Prompt eingefügt

#### Beispiel-Verarbeitung

**Ursprüngliche Aufgabe:**
```
Translate a given text into the specified target language.
```

**Mit Parameter `language: French`:**
```
Translate a given text into the specified target language.

Parameters:
language: French

User message: Hello, how are you today?
```

#### Mehrere Parameter

```json
{
    "parameters": {
        "language": "Spanish",
        "style": "formal",
        "include_context": "true"
    }
}
```

Wird verarbeitet zu:
```
Parameters:
language: Spanish
style: formal
include_context: true
```

## Verwaltung über das Admin Panel

### Zugriff auf das Admin Panel

1. Starten Sie die KIGate-Anwendung
2. Navigieren Sie zu: `http://localhost:8000/admin`
3. Melden Sie sich mit Admin-Zugangsdaten an
4. Wählen Sie "Agenten" aus dem Menü

### Agent erstellen

1. **Klicken Sie auf "Neuer Agent"**
2. **Füllen Sie die Pflichtfelder aus:**
   - Name: Eindeutiger Bezeichner
   - Beschreibung: Kurze Erklärung der Funktion
   - Rolle: System-Prompt für den Agenten
   - Provider: Wählen Sie den KI-Provider
   - Modell: Spezifisches Modell auswählen
   - Aufgabe: Detaillierte Anweisungen

3. **Parameter definieren (optional):**
   ```yaml
   - Inputtext:
       type: string
       description: Der zu verarbeitende Text
   - Model:
       type: string
       description: Das zu verwendende Modell
       default: gpt-4
   ```

4. **Speichern**: Der Agent wird als YAML-Datei gespeichert

### Agent bearbeiten

1. Wählen Sie den Agent aus der Liste
2. Klicken Sie auf "Bearbeiten"
3. Ändern Sie die gewünschten Felder
4. Speichern Sie die Änderungen

**⚠️ Hinweis:** Das Ändern des Namens erstellt eine neue YAML-Datei und löscht die alte.

### Agent löschen

1. Wählen Sie den Agent aus der Liste
2. Klicken Sie auf "Löschen"
3. Bestätigen Sie die Löschung

**⚠️ Warnung:** Gelöschte Agenten können nicht wiederhergestellt werden.

### Agent klonen

1. Wählen Sie den Agent aus der Liste
2. Klicken Sie auf "Klonen"
3. Ein neuer Agent mit dem Suffix "-clone" wird erstellt

## Beispiel-Agenten

### 1. Übersetzungsagent

```yaml
name: translation-agent
description: "Übersetzt Texte in verschiedene Sprachen"
role: "Du bist ein Übersetzungsagent."
provider: openai
model: gpt-4
task: |
  Übersetze den gegebenen Text in die Zielsprache.
  
  Anweisungen:
  - Übersetze präzise und originalgetreu
  - Bewahre Bedeutung, Ton und Stil
  - Füge keine Informationen hinzu oder entferne welche
  - Keine Halluzinationen - nutze nur die Informationen aus dem Quelltext
  
  Ausgabeformat: Nur der übersetzte Text, ohne Erklärungen.

parameters:
  - language:
      type: string
      description: "Die Zielsprache für die Übersetzung"
      default: "deutsch"
```

**API-Verwendung:**
```json
{
    "agent_name": "translation-agent",
    "provider": "openai",
    "model": "gpt-4",
    "message": "Hello, how are you today?",
    "user_id": "user-123-456",
    "parameters": {
        "language": "Spanish"
    }
}
```

### 2. Textoptimierungsagent

```yaml
name: text-optimization-agent
description: "Verbessert Texte in Bezug auf Grammatik und Stil"
role: "Du bist ein Textoptimierungsagent."
provider: openai
model: gpt-4
task: |
  Verbessere den gegebenen Text nur in Bezug auf Rechtschreibung, 
  Grammatik, Interpunktion und Textfluss.
  
  Anweisungen:
  - Prüfe auf Rechtschreib-, Grammatik- und Interpunktionsfehler
  - Optimiere Satzstruktur und Textfluss für bessere Lesbarkeit
  - Bewahre den ursprünglichen Inhalt, Bedeutung und Ton
  - Füge keine neuen Informationen hinzu
  - Gib den Text in derselben Sprache zurück
  
  Ausgabeformat: Nur der optimierte Text, ohne Erklärungen.

parameters:
  - optimization_level:
      type: string
      description: "Grad der Optimierung (leicht, mittel, stark)"
      default: "mittel"
```

**API-Verwendung:**
```json
{
    "agent_name": "text-optimization-agent",
    "provider": "openai",
    "model": "gpt-4",
    "message": "Dies ist ein text mit einigen fehlern und schlchte grammatik.",
    "user_id": "user-123-456",
    "parameters": {
        "optimization_level": "stark"
    }
}
```

### 3. Inhaltsbewertungsagent

```yaml
name: exam-content-agent
description: "Bewertet Essays hinsichtlich Argumentation, Struktur und Quellen"
role: "Du bist ein Inhaltsagent für wissenschaftliche Prüfungen"
provider: openai
model: gpt-4
task: |
  Bewerte Essays anhand der Qualität der Argumentation, 
  der logischen Struktur und der korrekten Nutzung von Quellen.
  
  Bewertungskriterien:
  - Argumentation: Sind die Thesen klar? Ist die Argumentation schlüssig?
  - Struktur: Ist der Text logisch gegliedert? Gibt es einen roten Faden?
  - Quellen: Sind die Quellen relevant, wissenschaftlich und korrekt zitiert?
  
  Ergebnis:
  - Prozentuale Bewertung (0-100%)
  - Schriftliches Feedback (1200-1500 Zeichen)

parameters:
  - Inputtext:
      type: string
      description: "Der zu bewertende Essay"
  - Bewertungsschema:
      type: string
      description: "Spezifisches Bewertungsschema"
      default: "standard"
```

## Best Practices

### 1. Naming Convention

- **Verwenden Sie sprechende Namen**: `translation-agent` statt `agent1`
- **Nutzen Sie Bindestriche**: `text-optimization-agent`
- **Vermeiden Sie Sonderzeichen**: Nur Buchstaben, Zahlen, Bindestriche und Unterstriche
- **Kurz und prägnant**: Maximal 100 Zeichen

### 2. Aufgabendefinition

- **Seien Sie spezifisch**: Klare, eindeutige Anweisungen
- **Verwenden Sie Beispiele**: Zeigen Sie gewünschte Ausgabeformate
- **Definieren Sie Grenzen**: Was soll der Agent NICHT tun?
- **Strukturieren Sie mit YAML**: Nutzen Sie `|` für mehrzeilige Texte

### 3. Parameter-Design

- **Sinnvolle Defaults**: Setzen Sie praktische Standardwerte
- **Klare Beschreibungen**: Erklären Sie jeden Parameter ausführlich
- **Validation**: Bedenken Sie, welche Werte sinnvoll sind
- **Konsistenz**: Nutzen Sie einheitliche Parameternamen

### 4. Provider und Modell

- **Wählen Sie passende Modelle**: `gpt-4` für komplexe Aufgaben, `gpt-3.5-turbo` für einfache
- **Bedenken Sie Kosten**: Größere Modelle sind teurer
- **Testen Sie verschiedene Provider**: OpenAI, Claude, etc.

### 5. Testing und Validation

- **Testen Sie Ihren Agent**: Verwenden Sie das Admin Panel zum Testen
- **Validieren Sie Eingaben**: Prüfen Sie Parameter-Kombinationen
- **Iterieren Sie**: Verbessern Sie basierend auf Ergebnissen

### 6. Dokumentation

- **Beschreibung**: Erklären Sie den Zweck des Agenten
- **Verwendung**: Dokumentieren Sie typische Anwendungsfälle
- **Parameter**: Erklären Sie alle Parameter ausführlich

## Troubleshooting

### Häufige Probleme

#### 1. YAML-Parsing Fehler

**Problem:** "Fehler beim Parsen der Parameter"

**Lösung:**
- Prüfen Sie die YAML-Syntax mit einem Online-Validator
- Achten Sie auf korrekte Einrückungen (2 Leerzeichen)
- Verwenden Sie Anführungszeichen für Sonderzeichen
- Nutzen Sie `|` für mehrzeilige Texte

**Beispiel für korrektes YAML:**
```yaml
parameters:
  - Inputtext:
      type: string
      description: "Der Eingabetext"
  - Settings:
      type: string
      description: "Konfiguration im JSON-Format"
      default: '{"temperature": 0.7}'
```

#### 2. Agent wird nicht gefunden

**Problem:** "Agent with name 'xyz' not found"

**Mögliche Ursachen:**
- Dateiname stimmt nicht mit Agent-Name überein
- YAML-Datei ist beschädigt oder unvollständig
- Pflichtfelder fehlen

**Lösung:**
- Prüfen Sie, ob alle Pflichtfelder vorhanden sind
- Überprüfen Sie die Datei im `agents/` Verzeichnis
- Laden Sie den Agent über das Admin Panel neu

#### 3. Validierungsfehler

**Problem:** Felder sind zu kurz/lang oder fehlen

**Lösung:**
- **Name**: 1-100 Zeichen, keine Sonderzeichen außer `-` und `_`
- **Description**: 1-500 Zeichen
- **Role**: 1-200 Zeichen  
- **Provider**: 1-50 Zeichen
- **Model**: 1-100 Zeichen
- **Task**: Mindestens 1 Zeichen

#### 4. Parameter-Probleme

**Problem:** Parameter werden nicht korrekt verarbeitet

**Lösung:**
```yaml
# ✅ Korrekt
parameters:
  - ParameterName:
      type: string
      description: "Beschreibung"
      
# ❌ Falsch
parameters:
  ParameterName: string  # Fehlende Struktur
```

### Debug-Tipps

1. **Verwenden Sie das Admin Panel**: Testen Sie Agenten direkt in der Web-Oberfläche
2. **Prüfen Sie Log-Ausgaben**: Schauen Sie in die Konsole für Fehlermeldungen
3. **Validieren Sie YAML**: Nutzen Sie Online-YAML-Validatoren
4. **Testen Sie schrittweise**: Beginnen Sie mit minimalen Agenten und erweitern Sie sukzessive
5. **Backup**: Sichern Sie funktionierende Agent-Konfigurationen

### Unterstützung

Bei weiteren Problemen:
1. Prüfen Sie die Konsolen-Ausgabe der Anwendung
2. Validieren Sie Ihre YAML-Syntax
3. Testen Sie mit einem einfachen Agent
4. Konsultieren Sie die Beispiel-Agenten im `agents/` Verzeichnis

---

## Weitere Ressourcen

- [KIGate API Dokumentation](http://localhost:8000/docs)
- [Admin Panel](http://localhost:8000/admin)
- [Beispiel-Agenten im Repository](./agents/)