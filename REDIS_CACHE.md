# Redis Cache für KIGate Agenten

## Übersicht

Der KIGate Agent Execution Endpoint (`/agent/execute`) unterstützt Redis-basiertes Caching, um Kosten zu senken und die Latenz bei wiederholten identischen Anfragen zu reduzieren.

## Funktionsweise

Das Caching verwendet eine **Cache-Aside-Strategie**:

1. Prüfen, ob das Ergebnis im Cache liegt
2. Bei **Cache-Hit**: Sofortige Rückgabe des gecachten Ergebnisses
3. Bei **Cache-Miss**: Agent ausführen und Ergebnis im Cache speichern

## Konfiguration

### Umgebungsvariablen

Fügen Sie folgende Variablen zu Ihrer `.env` Datei hinzu:

```bash
# Redis Configuration
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional, leer lassen wenn kein Passwort

# Cache TTL Configuration
CACHE_DEFAULT_TTL=21600  # 6 Stunden in Sekunden
CACHE_ERROR_TTL=60       # 60 Sekunden für Fehlerantworten
```

### Standard-Werte

Wenn Redis nicht verfügbar ist, arbeitet die Anwendung normal weiter (Graceful Degradation).

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `REDIS_ENABLED` | `true` | Cache aktivieren/deaktivieren |
| `REDIS_HOST` | `localhost` | Redis Server Host |
| `REDIS_PORT` | `6379` | Redis Server Port |
| `REDIS_DB` | `0` | Redis Datenbank Nummer |
| `CACHE_DEFAULT_TTL` | `21600` | Standard TTL (6 Stunden) |
| `CACHE_ERROR_TTL` | `60` | TTL für Fehlerantworten |

## Request-Parameter

### Neue optionale Parameter

```json
{
  "agent_name": "example-agent",
  "provider": "openai",
  "model": "gpt-4",
  "message": "Your message",
  "user_id": "user-123",
  "use_cache": true,        // Cache aktivieren/deaktivieren (Standard: true)
  "force_refresh": false,   // Cache ignorieren und neu ausführen (Standard: false)
  "cache_ttl": 3600         // Eigene TTL in Sekunden (Optional)
}
```

### Parameter-Beschreibung

- **`use_cache`** (bool, Standard: `true`)
  - Aktiviert oder deaktiviert das Caching für diese Anfrage
  - Bei `false` wird das Ergebnis nicht gecacht und nicht aus dem Cache gelesen

- **`force_refresh`** (bool, Standard: `false`)
  - Ignoriert existierenden Cache und erzwingt eine Neuberechnung
  - Das neue Ergebnis wird anschließend gecacht
  - Nützlich, wenn Sie ein frisches Ergebnis benötigen

- **`cache_ttl`** (int, optional)
  - Eigene Time-To-Live in Sekunden
  - Überschreibt die Standard-TTL für diese spezifische Anfrage
  - Wenn nicht angegeben: `CACHE_DEFAULT_TTL` für erfolgreiche Antworten, `CACHE_ERROR_TTL` für Fehler

## Response-Metadaten

Die Antwort enthält jetzt zusätzliche Cache-Metadaten:

```json
{
  "job_id": "job-123",
  "agent": "example-agent",
  "provider": "openai",
  "model": "gpt-4",
  "status": "completed",
  "result": "Agent response...",
  "cache": {
    "status": "hit",                      // "hit", "miss", oder "bypassed"
    "cached_at": "2024-01-15T10:30:00Z",  // Zeitstempel des Cachings
    "ttl": 21600                          // Verbleibende TTL in Sekunden
  }
}
```

### Cache Status

- **`hit`**: Ergebnis aus dem Cache
- **`miss`**: Ergebnis neu berechnet und gecacht
- **`bypassed`**: Cache wurde nicht verwendet (`use_cache=false`)

## Cache-Key-Schema

Cache-Keys folgen diesem Format:

```
kigate:v1:agent-exec:{agent_name}:{provider}:{model}:u:{user_id}:h:{sha256_hash}
```

Der SHA256-Hash wird aus folgenden Komponenten generiert:
- Nachricht (message)
- Parameter (sortiert für Konsistenz)

**Beispiel:**
```
kigate:v1:agent-exec:translator:openai:gpt-4:u:user-123:h:a1b2c3d4...
```

## Verwendungsbeispiele

### Beispiel 1: Normaler Request mit Cache

```bash
curl -X POST "https://kigate.example.com/agent/execute" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "translator",
    "provider": "openai",
    "model": "gpt-4",
    "message": "Hello World",
    "user_id": "user-123",
    "parameters": {
      "target_language": "de"
    }
  }'
```

**Erste Anfrage** → Cache Miss (Ergebnis wird berechnet und gecacht)
**Zweite identische Anfrage** → Cache Hit (Ergebnis aus Cache)

### Beispiel 2: Cache deaktivieren

```json
{
  "agent_name": "translator",
  "message": "Hello World",
  "user_id": "user-123",
  "use_cache": false
}
```

### Beispiel 3: Cache-Refresh erzwingen

```json
{
  "agent_name": "translator",
  "message": "Hello World",
  "user_id": "user-123",
  "force_refresh": true
}
```

### Beispiel 4: Eigene TTL setzen

```json
{
  "agent_name": "translator",
  "message": "Hello World",
  "user_id": "user-123",
  "cache_ttl": 7200
}
```

## Cache-Separierung

Separate Cache-Einträge werden erstellt für:

- ✅ Verschiedene Benutzer
- ✅ Verschiedene Agenten
- ✅ Verschiedene Provider
- ✅ Verschiedene Modelle
- ✅ Verschiedene Nachrichten
- ✅ Verschiedene Parameter

**Beispiel:**
```
User A + Agent X + Message "Hello" → Cache Entry 1
User B + Agent X + Message "Hello" → Cache Entry 2 (separater Cache!)
```

## Concurrency Handling

Das System verwendet Redis-Locks, um zu verhindern, dass dieselbe Anfrage mehrfach gleichzeitig ausgeführt wird:

1. Anfrage prüft Cache → Miss
2. Lock wird erworben (SETNX mit Timeout)
3. Agent wird ausgeführt
4. Ergebnis wird gecacht
5. Lock wird freigegeben

Falls eine zweite identische Anfrage während der Ausführung eintrifft, kann sie optional auf die Fertigstellung warten.

## Performance & Vorteile

### Vorteile

- 🚀 **Schnellere Antworten**: Cache-Hits liefern Ergebnisse in <50ms
- 💰 **Kostenreduktion**: Weniger API-Aufrufe an AI-Provider
- 📊 **Skalierbarkeit**: Reduzierte Last auf Backend-Dienste
- 🔒 **Konsistenz**: Identische Anfragen erhalten identische Antworten

### Typische Szenarien

| Szenario | Ohne Cache | Mit Cache |
|----------|------------|-----------|
| Erste Anfrage | 2-5 Sekunden | 2-5 Sekunden (Cache Miss) |
| Wiederholte Anfrage | 2-5 Sekunden | <50ms (Cache Hit) |
| API-Kosten | 100% | ~20-50% (je nach Wiederholungsrate) |

## Monitoring

### Logs

Cache-Aktivitäten werden geloggt:

```
INFO - Cache HIT for key: kigate:v1:agent-exec:translator:openai...
INFO - Cache MISS for key: kigate:v1:agent-exec:translator:openai...
INFO - Cached result for key: kigate:v1:agent-exec:translator:openai... (TTL: 21600s)
```

### Cache-Statistiken

Cache-Metadaten in jeder Response ermöglichen Monitoring:
- Anzahl Cache Hits
- Anzahl Cache Misses
- Durchschnittliche TTL
- Cache Hit Rate

## Troubleshooting

### Redis nicht erreichbar

**Symptom**: Warnung im Log: "Redis connection failed"

**Lösung**: 
1. Prüfen Sie die Redis-Konfiguration
2. Stellen Sie sicher, dass Redis läuft: `redis-cli ping`
3. Die Anwendung läuft weiter ohne Cache (Graceful Degradation)

### Cache wird nicht verwendet

**Mögliche Ursachen**:
1. `use_cache=false` im Request
2. `REDIS_ENABLED=false` in der Konfiguration
3. Redis nicht verfügbar

**Prüfen**:
- Response enthält `"cache": {"status": "bypassed"}` → `use_cache=false`
- Log-Nachricht "Redis cache is disabled" → `REDIS_ENABLED=false`

### Unerwartete Cache Misses

**Ursachen**:
- Leichte Unterschiede in Parametern (Groß-/Kleinschreibung, Leerzeichen)
- Verschiedene User-IDs
- TTL abgelaufen

**Lösung**: 
- Prüfen Sie Request-Parameter auf Konsistenz
- Erhöhen Sie `cache_ttl` für länger gültige Caches

## Best Practices

1. **Standard-Cache verwenden**: Lassen Sie `use_cache=true` für die meisten Anfragen
2. **Force-Refresh sparsam einsetzen**: Nur wenn frische Daten kritisch sind
3. **Passende TTL wählen**: 
   - Statische Inhalte: 24h+
   - Dynamische Inhalte: 1-6h
   - Zeitkritische Daten: 5-30min
4. **Parameter konsistent halten**: Gleiche Schreibweise, Reihenfolge unwichtig
5. **Cache-Metadaten nutzen**: Überwachen Sie Hit-Rates für Optimierung

## Sicherheit

- Cache-Keys enthalten keine sensitiven Daten (nur Hashes)
- Jeder User hat separaten Cache-Namespace
- Redis sollte durch Firewall geschützt sein
- Optional: Redis-Passwort verwenden (`REDIS_PASSWORD`)

## Weiterführende Informationen

- [Redis Documentation](https://redis.io/documentation)
- [Cache-Aside Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/cache-aside)
- KIGate API Documentation: `/docs`
