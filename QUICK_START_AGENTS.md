# KIGate Agenten - Schnellstart Guide

Ein kompakter Leitfaden für den schnellen Einstieg in die Agent-Erstellung.

## 5-Minuten Schnellstart

### 1. Agent erstellen (Admin Panel)

1. **Öffnen Sie**: `http://localhost:8000/admin/agents`
2. **Klicken Sie**: "Neuer Agent"
3. **Füllen Sie aus**:

```
Name: mein-test-agent
Beschreibung: Macht einfache Textverarbeitung
Rolle: Du bist ein hilfreicher Textassistent
Provider: openai
Modell: gpt-3.5-turbo
Aufgabe: Verbessere den gegebenen Text und mache ihn lesbarer.
```

4. **Parameter** (optional):
```yaml
- input_text:
    type: string
    description: "Der zu verarbeitende Text"
- style:
    type: string
    description: "Gewünschter Stil"
    default: "neutral"
```

5. **Speichern**

### 2. Agent per YAML erstellen

Erstellen Sie eine Datei `agents/mein-agent.yml`:

```yaml
name: mein-agent
description: "Ein einfacher Textverbesserungs-Agent"
role: "Du bist ein Textassistent"
provider: openai
model: gpt-3.5-turbo
task: |
  Verbessere den gegebenen Text:
  - Korrigiere Grammatik und Rechtschreibung
  - Verbessere die Lesbarkeit
  - Behalte die ursprüngliche Bedeutung bei

parameters:
  - input_text:
      type: string
      description: "Der zu verarbeitende Text"
  - style:
      type: string
      description: "Gewünschter Schreibstil"
      default: "formal"
```

### 3. Häufige Agent-Typen

#### Übersetzungsagent
```yaml
name: uebersetzer
description: "Übersetzt Texte zwischen Sprachen"
role: "Du bist ein professioneller Übersetzer"
provider: openai
model: gpt-4
task: "Übersetze den Text in die Zielsprache. Bewahre Bedeutung und Stil."
parameters:
  - language:
      type: string
      description: "Zielsprache"
      default: "Deutsch"
```

**API-Verwendung:**
```bash
curl -X POST "https://kigate.isarlabs.de/agent/execute" \
     -H "Authorization: Bearer your_client_id:your_client_secret" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_name": "uebersetzer",
       "provider": "openai",
       "model": "gpt-4",
       "message": "Hello world!",
       "user_id": "user-123",
       "parameters": {
         "language": "French"
       }
     }'
```

#### Zusammenfassungsagent
```yaml
name: zusammenfasser
description: "Erstellt Zusammenfassungen von Texten"
role: "Du bist ein Experte für Textzusammenfassungen"
provider: openai
model: gpt-4
task: "Erstelle eine präzise Zusammenfassung des Textes. Fokussiere auf die Hauptpunkte."
parameters:
  - length:
      type: string
      description: "Gewünschte Länge"
      default: "kurz"
```

**API-Verwendung:**
```json
{
    "agent_name": "zusammenfasser",
    "provider": "openai",
    "model": "gpt-4",
    "message": "Ein sehr langer Text der zusammengefasst werden soll...",
    "user_id": "user-123",
    "parameters": {
        "length": "ausführlich"
    }
}
```

#### Analyseagent
```yaml
name: text-analyzer
description: "Analysiert Texte auf Stil und Inhalt"
role: "Du bist ein Textanalyst"
provider: openai
model: gpt-4
task: |
  Analysiere den Text auf:
  - Stil und Ton
  - Hauptthemen
  - Verbesserungsvorschläge
parameters:
  - focus:
      type: string
      description: "Analyseschwerpunkt"
      default: "allgemein"
```

**API-Verwendung:**
```json
{
    "agent_name": "text-analyzer",
    "provider": "openai",
    "model": "gpt-4",
    "message": "Zu analysierender Text hier...",
    "user_id": "user-123",
    "parameters": {
        "focus": "grammatik"
    }
}
```

## Checkliste für neue Agenten

### ✅ Pflichtfelder prüfen
- [ ] `name` - eindeutig, ohne Sonderzeichen
- [ ] `description` - kurz und prägnant
- [ ] `role` - klarer System-Prompt
- [ ] `provider` - gültiger Provider (openai, claude)
- [ ] `model` - verfügbares Modell
- [ ] `task` - detaillierte Aufgabenbeschreibung

### ✅ Parameter definieren
- [ ] `Inputtext` - für Texteingabe
- [ ] Weitere spezifische Parameter
- [ ] Standardwerte setzen
- [ ] Klare Beschreibungen

### ✅ Testing
- [ ] Agent über Admin Panel testen
- [ ] Verschiedene Eingaben ausprobieren
- [ ] Ausgabequalität prüfen

## Häufige Fehler vermeiden

❌ **Falsch:**
```yaml
name: My Agent 123!  # Leerzeichen und Sonderzeichen
provider: chatgpt    # Falscher Provider-Name
task: "Do something" # Zu unspezifisch
```

✅ **Richtig:**
```yaml
name: my-agent-123
provider: openai
task: |
  Spezifische Aufgabe:
  - Schritt 1
  - Schritt 2
  - Gewünschtes Format
```

## Parameter in API-Calls verwenden

### Mit Parameter
```bash
curl -X POST "http://localhost:8000/agent/execute" \
     -H "Authorization: Bearer your_token" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_name": "translation-agent",
       "provider": "openai",
       "model": "gpt-4",
       "message": "Hello world!",
       "user_id": "user-123",
       "parameters": {
         "language": "Spanish"
       }
     }'
```

### Ohne Parameter
```bash
curl -X POST "http://localhost:8000/agent/execute" \
     -H "Authorization: Bearer your_token" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_name": "translation-agent",
       "provider": "openai",
       "model": "gpt-4",
       "message": "Translate to French: Hello world!",
       "user_id": "user-123"
     }'
```

### Mehrere Parameter
```bash
curl -X POST "http://localhost:8000/agent/execute" \
     -H "Authorization: Bearer your_token" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_name": "text-analyzer",
       "provider": "openai",
       "model": "gpt-4",
       "message": "Text to analyze...",
       "user_id": "user-123",
       "parameters": {
         "focus": "style",
         "detail_level": "high",
         "language": "German"
       }
     }'
```

## Weiterführende Dokumentation

- **[Vollständige Agent-Dokumentation](README_AGENTS.md)** - Detaillierte Erklärungen
- **[API-Dokumentation](API_Documentation.md)** - Vollständige API-Referenz
- **[Hauptdokumentation](README.md)** - Allgemeine Informationen
- **Admin Panel**: `http://localhost:8000/admin/agents`
- **API Docs**: `http://localhost:8000/docs`

---

💡 **Tipp**: Beginnen Sie mit einfachen Agenten und erweitern Sie diese schrittweise!