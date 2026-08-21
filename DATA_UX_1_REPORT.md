# UX-1 / DATA-UX-1 — Estado compartible y vocabularios de filtro

Fecha: 21 de agosto de 2026.

## Alcance

Esta fase no cambia cobertura, fuentes ni identidad de incendios. Añade una
capa derivada reproducible para municipio y causa, un permalink versionado y
ajustes de ámbito del frontend. Raw y normalized permanecen intactos.

## Municipios

La entrada es el catálogo oficial ICV de 542 términos municipales conservado
por CV-2.2. `scripts/filter_vocabularies.py` enriquece los derivados web con:

- `municipality_raw`: texto fuente sin sustituir;
- `municipality_id`: código INE cuando la correspondencia está demostrada;
- `municipality_name`: denominación de visualización del catálogo.

Resultados sobre ICV, SIGIF y EFFIS locales:

| Medida | Resultado |
|---|---:|
| nombres raw no vacíos distintos | 811 |
| municipios oficiales usados | 492 |
| registros resueltos | 14.154 |
| registros sin municipio | 12 |
| registros ambiguos (más de un candidato) | 0 |
| registros inicialmente no resueltos | 244 |
| valores raw inicialmente no resueltos | 28 |
| registros todavía no resueltos tras auditoría | 21 |
| valores raw todavía no resueltos | 13 |
| municipios con más de una variante raw resuelta | 214 |

La revisión final resuelve 223 de los 244 registros: 166 mediante componentes
exactos de denominaciones oficiales bilingües que convergen en un único código
de la provincia y 57 mediante cambios de nombre documentados oficialmente:
`Herbés → Herbers` (9) y `Villanueva de Castellón → Castelló` (48). No se ha
usado similitud textual para resolver. Quedan 21 registros: 19 requieren
evidencia adicional y 2 contienen un marcador de «otra provincia», no un
municipio.

El informe JSON y la tabla CSV reproducibles quedan, ignorados, en
`data/derived/gva/data-ux-1/report.json` y
`data/derived/gva/data-ux-1/municipality_unresolved_audit.csv`.

### Auditoría de los 28 valores iniciales

Todos proceden de ICV y carecen de código municipal original público. Los
candidatos marcados como `textual_only` o `abbreviated_name_only` se registran
para revisión, pero **no** se asignan.

| municipality_raw | N | Fuente | Años | Provincia | Código fuente | Candidatos oficiales | Motivo | Recomendación |
|---|---:|---|---|---|---|---|---|---|
| `Alqueries (les)/Alquerías del Niño Perdido` | 1 | ICV | 2005 | Castellón/Castelló | — | 12901 les Alqueries (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `Benitachell/Poble Nou de Benitatxell (el)` | 11 | ICV | 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2001, 2002, 2004 | Alicante/Alacant | — | 03042 el Poble Nou de Benitatxell (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `CASTELLÓ/CASTELLÓ DE LA RIBERA` | 1 | ICV | 2019 | Valencia | — | 46257 Castelló (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `CASTIELFABID` | 1 | ICV | 2019 | Valencia | — | 46092 Castielfabib (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `Campo de Mirra/Camp de Mirra (el)` | 1 | ICV | 2001 | Alicante/Alacant | — | 03051 el Camp de Mirra (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `Cas. Iniciado otra provincia` | 1 | ICV | 2017 | Castellón | — | — | no es un municipio | `keep_unresolved` |
| `Castellón de la Plana/Castelló` | 1 | ICV | 2016 | Castellón | — | 12040 Castelló de la Plana (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `FONTANARS DELS AFORINS` | 1 | ICV | 2019 | Valencia | — | 46124 Fontanars dels Alforins (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `Fondón de les Neus (el)/Hondón de las Nieves` | 9 | ICV | 1993, 1994, 2004, 2006, 2008, 2010, 2015 | Alicante/Alacant | — | 03077 el Fondó de les Neus (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `Fontanars dels Aforins` | 3 | ICV | 2018 | Valencia | — | 46124 Fontanars dels Alforins (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `Herbés` | 9 | ICV | 1995, 1996, 1998, 2000, 2002, 2003, 2004, 2007 | Castellón/Castelló | — | 12068 Herbers | cambio documentado en BOE-A-2020-12459 | `resolve_safe` |
| `L'Alcora/Alcora` | 10 | ICV | 2016, 2017, 2018 | Castellón | — | 12005 l'Alcora (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `L'Alqueria de Asnar` | 1 | ICV | 2016 | Alicante | — | 03017 l'Alqueria d'Asnar (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `La Mata` | 1 | ICV | 2018 | Castellón | — | 12075 la Mata de Morella (solo abreviado) | sin equivalencia demostrada | `needs_human_review` |
| `La Vall de Laguart` | 1 | ICV | 2018 | Alicante | — | 03137 la Vall de Laguar (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `Lorcha/Orxa (l')` | 41 | ICV | 1993–2015 (16 años con registros) | Alicante/Alacant | — | 03084 l'Orxa (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `Otra Provincia` | 1 | ICV | 2020 | Valencia/València | — | — | no es un municipio | `keep_unresolved` |
| `POLINYÀ DEL XÚQUER` | 2 | ICV | 2019 | Valencia | — | 46197 Polinyà de Xúquer (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `Polinyà del Xúquer` | 2 | ICV | 2016, 2018 | Valencia | — | 46197 Polinyà de Xúquer (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `RIBA-ROJA DEL TÚRIA` | 3 | ICV | 2019 | Valencia | — | 46214 Riba-roja de Túria (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `SAN JORDI/SAN JORGE` | 1 | ICV | 2019 | Castellón | — | 12099 Sant Jordi (componente exacto) | componente castellano exacto | `resolve_safe` |
| `SAN MATEU` | 3 | ICV | 2019 | Castellón | — | 12100 Sant Mateu (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `SOT CHERA` | 1 | ICV | 2019 | Valencia | — | 46234 Sot de Chera (solo textual) | sin equivalencia demostrada | `needs_human_review` |
| `Torremanzanas/Torre de les Maçanes (la)` | 25 | ICV | 1993–2014 (13 años con registros) | Alicante/Alacant | — | 03132 la Torre de les Maçanes (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `Useras/Useres (les)` | 32 | ICV | 1993–2014 (19 años con registros) | Castellón/Castelló | — | 12122 les Useres (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `VILA JOIOSA, LA/VILLAJOYOSA` | 1 | ICV | 2019 | Alicante | — | 03139 la Vila Joiosa (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `Villajoyosa/Vila Joiosa (la)` | 32 | ICV | 1994–2015 (17 años con registros) | Alicante/Alacant | — | 03139 la Vila Joiosa (componente exacto) | componentes exactos del catálogo | `resolve_safe` |
| `Villanueva de Castellón` | 48 | ICV | 1993–2018 (16 años con registros) | Valencia/València | — | 46257 Castelló | cambio documentado en BOE-A-2020-12460 | `resolve_safe` |

### Caso Elx

El código `03065`, visualizado como `Elx`, reúne 181 registros y cinco textos
fuente: `ELX/ELCHE` (3), `Elche / Elx` (1), `Elche/Elx` (135), `Elx` (19) y
`Elx/Elche` (23). El selector ofrece una sola opción `Elx` y filtra por
`municipality_id=03065`.

## Causas

Se encontraron 14 textos raw distintos. Todos tienen mapeo explícito; EFFIS no
aporta causa y conserva `null`. El vocabulario de interfaz tiene ocho valores:

| `cause_code` | Etiqueta |
|---|---|
| `intentional` | Intencionado |
| `lightning` | Rayo |
| `negligence` | Negligencia |
| `negligence_and_accidental` | Negligencias y causas accidentales |
| `rekindle` | Incendio reproducido |
| `other` | Otras causas |
| `unknown` | Desconocida |
| `under_investigation` | En investigación |

Las variantes morfológicas o de mayúsculas se agrupan solo dentro de estos
conceptos. «Desconocida» y «En investigación» siguen separadas; también lo
hacen «Negligencia» y la categoría histórica que incluye causas accidentales.

## Permalink

Formato estable inicial:

```text
#v=1&lat=38.27000&lng=-0.70000&z=8&from=1994&to=1994&src=icv&province=alicante&municipality=03065&min_area=0&gif=0&cause=intentional
```

Comparte centro, zoom, rango anual, fuentes, provincia, municipio, superficie
mínima, GIF, causa y, opcionalmente, `entity` y `geometry`. Parámetros inválidos
o desconocidos se ignoran. La selección se restaura cuando la entidad existe en
los bloques requeridos por esa misma vista; de lo contrario la vista sigue
siendo utilizable sin selección.

## Interfaz y perfiles

El acceso principal se denomina «País Valencià» y ofrece las tres provincias.
Mariola–Font Roja deja de ser botón principal, pero
`?view=mariola_font_roja` continúa operativo. Las denominaciones oficiales de
datasets y atribuciones no cambian.

El perfil `development` muestra ICV, SIGIF y EFFIS. El perfil `public` obtiene
solo ICV y EFFIS del manifiesto; el control, leyenda y explicación de
correspondencias SIGIF permanecen ocultos. El bundle público reproducible
`public-data-v2` contiene los derivados canónicos y mantiene fuera SIGIF,
candidatos, EGIF, raw, processed y benchmarks.

Los contadores en selectores se posponen: al combinar fuentes, `N` podría
significar incendios ICV, filas administrativas SIGIF o perímetros EFFIS, y no
se mostrará una cifra ambigua.

## Validación y coste

La suite Python pasa 18 pruebas. Chrome headless pasa 25 escenarios de
desarrollo y 24 del perfil público bajo `/atlas-incendios/`, incluidos hash
1994, 2026 EFFIS, GIF, superficie mínima, municipio, causa, selección, valores
inválidos, acción de compartir, reapertura en una sesión nueva y móvil. El
perfil público contiene únicamente controles ICV y EFFIS y el guard sigue
rechazando SIGIF.

Medianas de tres ejecuciones locales con Chrome:

| Escenario | Carga | Render | Heap | gzip estimado |
|---|---:|---:|---:|---:|
| inicio 2026, escritorio | 16,2 ms | 16,1 ms | 7,06 MiB | 89.116 B |
| ICV 2024 | 85,7 ms | 28,6 ms | 38,94 MiB | 988.563 B |
| periodo completo | 241,0 ms | 298,3 ms | 167,35 MiB | 3.197.980 B |
| inicio 2026, móvil 390×844 | 11,7 ms | 13,6 ms | 7,15 MiB | 89.116 B |

Los campos canónicos elevan `fires.json` de 5.848.959 a 7.654.881 bytes, pero
gzip solo pasa de 492.721 a 572.574 bytes. En el conjunto ICV de producción el
incremento gzip es 79.853 bytes (0,69 %). El render completo cambia poco frente
al benchmark CV-2.3 (292,6 → 298,3 ms); el heap completo crece aproximadamente
8,9 %. El arranque público 2026 solo carga EFFIS y no sufre el coste de
`fires.json`.
