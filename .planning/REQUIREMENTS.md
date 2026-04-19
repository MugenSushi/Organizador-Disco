# Requirements: Organizador de Disco

**Defined:** 2026-04-19
**Core Value:** Organizar una unidad seleccionada en segundos sin miedo a errores, gracias al dry-run y el undo.

## v1 Requirements

### Infraestructura

- [ ] **INFRA-01**: El script detecta todas las unidades extraíbles disponibles al arrancar (via ctypes.windll.kernel32 GetDriveTypeW)
- [ ] **INFRA-02**: El script pregunta al usuario cuál unidad usar y la valida antes de continuar
- [ ] **INFRA-03**: Todos los archivos con extensiones ROM/ISO son ignorados en cualquier operación (hard block: .iso .bin .cue .img .mdf .nrg .chd .gba .gbc .gb .nes .sfc .smc .n64 .z64 .3ds .cia .nds .gcm .wbfs .wad .xci .nsp)
- [ ] **INFRA-04**: Rutas del sistema son ignoradas en cualquier operación (System Volume Information, $RECYCLE.BIN, WindowsApps, Program Files, Amazon Games)
- [ ] **INFRA-05**: El escaneo de la unidad usa os.scandir (nunca glob/rglob) para soportar nombres con corchetes []
- [ ] **INFRA-06**: Todos los movimientos pasan por una clase Executor con flag dry_run centralizado
- [ ] **INFRA-07**: Los destinos nunca sobreescriben archivos existentes — sufijo (2), (3)... via _free_path()
- [ ] **INFRA-08**: Los logs de cada ejecución se guardan en <unidad>\_organizer_logs\ con encoding UTF-8

### Menú

- [ ] **MENU-01**: El script presenta un menú numerado en terminal al iniciar (sin argumentos CLI)
- [ ] **MENU-02**: Desde el menú se puede activar modo dry-run antes de ejecutar cualquier operación
- [ ] **MENU-03**: Al finalizar cualquier operación se muestra un resumen: archivos procesados, movidos, saltados, errores

### Renombrado

- [ ] **RENAME-01**: El usuario puede aplicar renombrados desde un rename_plan.tsv existente (columnas old_path / new_path, separador tab)
- [ ] **RENAME-02**: El aplicador de renombrados usa rutas literales (sin interpretar comodines)
- [ ] **RENAME-03**: El script puede generar automáticamente un rename_plan.tsv sugerido escaneando la unidad y detectando nombres mal formateados
- [ ] **RENAME-04**: El TSV generado se guarda en _organizer_logs\ para que el usuario lo revise antes de aplicar (nunca se auto-aplica)

### Organización

- [ ] **ORG-01**: Los archivos de vídeo con patrón "Show - Temporada X - Episodio Y" se mueven a Series\<Show>\Temporada X\
- [ ] **ORG-02**: Los archivos de vídeo con patrón "Título (Año)" se mueven a Peliculas\<Título (Año)>\
- [ ] **ORG-03**: Las carpetas PC, PS1, PS2, PSP, GBA, GBC se mueven a Juegos\<sistema>\ (contenido, no la carpeta como tal)
- [ ] **ORG-04**: Los subtítulos (.srt .ass .sub .idx) con el mismo basename que un vídeo se mueven junto a él
- [ ] **ORG-05**: Tras organizar, las carpetas que quedan vacías se eliminan (os.rmdir, nunca shutil.rmtree)

### Undo

- [ ] **UNDO-01**: Cada operación que mueve o renombra archivos queda registrada en un log JSON atómico
- [ ] **UNDO-02**: El log JSON guarda rutas relativas a la unidad más el número de serie del volumen (para sobrevivir cambios de letra de unidad)
- [ ] **UNDO-03**: Desde el menú el usuario puede revertir la última ejecución completa

### Coherencia

- [ ] **COH-01**: El script puede escanear la unidad y reportar vídeos fuera de las carpetas esperadas (Series, Peliculas)
- [ ] **COH-02**: El reporte detecta series con episodios sin carpeta de temporada asignada
- [ ] **COH-03**: El reporte detecta títulos duplicados por nombre normalizado (ignorando año, resolución, etc.)

## v2 Requirements

### Mejoras futuras

- **V2-01**: Soporte para patrones SxxExx (S01E05) además del formato "Temporada X - Episodio Y"
- **V2-02**: Integración opcional con TMDB/TVDB para validar nombres (requiere API key y dependencia externa)
- **V2-03**: Barra de progreso visual para drives grandes (>5000 archivos)
- **V2-04**: Modo watch: monitorizar la unidad y organizar automáticamente los archivos nuevos

## Out of Scope

| Feature | Reason |
|---------|--------|
| Argumentos CLI | El usuario prefiere menú interactivo; no es una herramienta de scripting |
| Organización de música o fotos | Fuera del dominio (medios de entretenimiento únicamente) |
| GUI gráfica | No pedida; la terminal cubre el caso de uso |
| APIs externas (TMDB, TVDB) | Añaden dependencias externas; los nombres ya siguen formato propio |
| shutil.rmtree en limpieza | Demasiado destructivo; solo os.rmdir para carpetas vacías |

## Traceability

*(Se completa al crear el roadmap)*

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 – INFRA-08 | — | Pending |
| MENU-01 – MENU-03 | — | Pending |
| RENAME-01 – RENAME-04 | — | Pending |
| ORG-01 – ORG-05 | — | Pending |
| UNDO-01 – UNDO-03 | — | Pending |
| COH-01 – COH-03 | — | Pending |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 23 ⚠️

---
*Requirements defined: 2026-04-19*
*Last updated: 2026-04-19 after initial definition*
