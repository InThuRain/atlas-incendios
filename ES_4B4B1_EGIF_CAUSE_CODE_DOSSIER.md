# ES-4B4B1 — Dossier de códigos de causa EGIF

## Alcance

Dossier determinista construido exclusivamente desde los agregados de ES-4B4A y documentación local ya conservada. No relee los 646.887 registros normalizados, no crea mappings nuevos y no convierte dimensiones secundarias en una causa canónica.

## Resumen

- Registros: **646,887**.
- Códigos `pif_causa.idcausa`: **87**.
- Códigos `documented`: **15**; frecuencia: **609,964**.
- Códigos `unmapped`: **72**; frecuencia: **36,923**.
- No hay evidencia documental local de cambio semántico de un mismo código entre regímenes; por ello ningún código queda marcado `semantic_change_possible=true`.

## Contrato semántico

- `null` no equivale a desconocida; desconocida no equivale a en investigación.
- Causa primaria, causante, motivación y certidumbre permanecen como dimensiones fuente separadas.
- La coincidencia de un código en más de un esquema no demuestra por sí misma que su significado haya cambiado ni que se mantenga idéntico.

## Regímenes de campos observados

- `egif_cause_schema_1`: 1968–2004 (36 años observados), campos: `pif_causa.idcausa`, `pif_causa.idcausante`, `pif_causa.idcertidumbrecausa`, `pif_causa.idclasedia`, `pif_causa.idmotivacion`.
- `egif_cause_schema_2`: 2001–2015 (12 años observados), campos: `pif_causa.diastormenta`, `pif_causa.idcausa`, `pif_causa.idcausante`, `pif_causa.idcertidumbrecausa`, `pif_causa.idclasedia`, `pif_causa.idmotivacion`.
- `egif_cause_schema_3`: 2016–2023 (8 años observados), campos: `pif_causa.causaotros`, `pif_causa.diastormenta`, `pif_causa.idautorizacionactividad`, `pif_causa.idcausa`, `pif_causa.idcausante`, `pif_causa.idcertidumbrecausa`, `pif_causa.idclasedia`, `pif_causa.idgradoresponsabilidad`, `pif_causa.idinvestigacioncausa`, `pif_causa.idmotivacion`, `pif_causa.motivacionotros`.

## Tabla completa de `idcausa`

Las listas completas de años, provincias/CCAA, ejemplos y la referencia documental de cada código se conservan en `data/audit/egif/es4b4b1_cause_codes.json`.

| Código | Etiqueta fuente local | Frecuencia | % nacional | Primero–último | Estado | Canónica actual | Ejemplo |
|---:|---|---:|---:|---|---|---|---|
| 100 | Causa: Rayo | 27,989 | 4.326722% | 1968–2023 | documented | lightning | `egif-record:1968020558` |
| 210 | Causa: Quema agrícola (s.e.) | 20,405 | 3.154338% | 1968–2023 | documented | negligence | `egif-record:1968030262` |
| 211 | Causa: Quemas de rastrojos | 2,608 | 0.403162% | 2005–2023 | unmapped | — | `egif-record:2005020066` |
| 212 | Causa: Quema agrícola (restos poda) | 4,188 | 0.647408% | 2005–2023 | unmapped | — | `egif-record:2005020019` |
| 213 | — | 337 | 0.052096% | 2016–2023 | unmapped | — | `egif-record:2016010015` |
| 214 | — | 156 | 0.024115% | 2016–2023 | unmapped | — | `egif-record:2016060284` |
| 215 | — | 31 | 0.004792% | 2016–2023 | unmapped | — | `egif-record:2016080006` |
| 216 | — | 588 | 0.090897% | 2016–2023 | unmapped | — | `egif-record:2016010001` |
| 220 | Causa: Otras quemas ganaderas (sin especificar) | 13,148 | 2.032503% | 1968–2023 | documented | negligence | `egif-record:1968020089` |
| 221 | Causa: Quema de matorral | 1,620 | 0.250430% | 2005–2023 | unmapped | — | `egif-record:2005020038` |
| 222 | Causa: Quema de herbáceas | 665 | 0.102800% | 2005–2023 | unmapped | — | `egif-record:2005060226` |
| 230 | Causa: Otras quemas en trabajos forestales (conocidas) | 7,760 | 1.199591% | 1968–2023 | documented | negligence | `egif-record:1968050056` |
| 231 | — | 1,293 | 0.199880% | 2016–2023 | unmapped | — | `egif-record:2016010023` |
| 240 | Causa: Otros tipos de hogueras (conocidas) | 6,591 | 1.018880% | 1968–2022 | documented | negligence | `egif-record:1968020250` |
| 241 | — | 529 | 0.081776% | 2016–2023 | unmapped | — | `egif-record:2016020033` |
| 242 | — | 52 | 0.008039% | 2016–2023 | unmapped | — | `egif-record:2016010007` |
| 243 | — | 113 | 0.017468% | 2016–2023 | unmapped | — | `egif-record:2016070051` |
| 244 | — | 344 | 0.053178% | 2016–2023 | unmapped | — | `egif-record:2016030009` |
| 250 | Causa: Fumadores | 14,958 | 2.312305% | 1968–2023 | documented | negligence | `egif-record:1968021738` |
| 260 | Causa: Otros incendios  por quema de basuras (conocidas) | 6,044 | 0.934321% | 1986–2023 | documented | negligence | `egif-record:1986480015` |
| 261 | — | 267 | 0.041275% | 2016–2023 | unmapped | — | `egif-record:2016040002` |
| 262 | — | 518 | 0.080076% | 2016–2023 | unmapped | — | `egif-record:2016020189` |
| 270 | Causa: Escape de vertedero | 2,045 | 0.316129% | 1997–2023 | unmapped | — | `egif-record:1997300049` |
| 280 | Causa: Otras quemas de limpieza (sin especificar) | 4,589 | 0.709397% | 1989–2023 | unmapped | — | `egif-record:1989277581` |
| 281 | Causa: Limpieza de vegetación próxima a edificaciones | 258 | 0.039883% | 2005–2023 | unmapped | — | `egif-record:2005020013` |
| 282 | Causa: Limpieza de accesos (pistas, caminos , sendas, etc) | 498 | 0.076984% | 2005–2023 | unmapped | — | `egif-record:2005060019` |
| 283 | Causa: Limpieza de vegetación para control de animales nocivos (plagas, conejos, etc.) | 98 | 0.015149% | 2005–2023 | unmapped | — | `egif-record:2005110025` |
| 284 | Causa: Limpieza de lindes y bordes de finca | 1,810 | 0.279802% | 2005–2023 | unmapped | — | `egif-record:2005020002` |
| 285 | — | 258 | 0.039883% | 2016–2023 | unmapped | — | `egif-record:2016060002` |
| 286 | Causa: Limpieza de infraestructuras de riego (acequias,cavas, etc.) | 909 | 0.140519% | 2005–2023 | unmapped | — | `egif-record:2005020018` |
| 290 | Causa: Otras causas no intencionales (sin determinar) | 14,889 | 2.301638% | 1968–2023 | documented | negligence | `egif-record:1968031144` |
| 291 | Causa: Apicultura | 271 | 0.041893% | 2005–2023 | unmapped | — | `egif-record:2005070131` |
| 292 | Causa: Fuegos artificiales (petardos, cohetes,etc.) | 730 | 0.112848% | 2005–2023 | unmapped | — | `egif-record:2005010030` |
| 293 | Causa: Globos aerostáticos | 19 | 0.002937% | 2005–2022 | unmapped | — | `egif-record:2005386001` |
| 294 | Causa: Gamberradas, juegos de niños (quema de pelusa de chopo, etc) | 1,899 | 0.293560% | 2005–2023 | unmapped | — | `egif-record:2005030015` |
| 295 | Causa: Quema de restos de poda o jardinería en urbanizaciones | 240 | 0.037101% | 2005–2023 | unmapped | — | `egif-record:2005030056` |
| 296 | — | 7 | 0.001082% | 2017–2022 | unmapped | — | `egif-record:2017370139` |
| 297 | — | 41 | 0.006338% | 2016–2023 | unmapped | — | `egif-record:2016030078` |
| 298 | — | 7 | 0.001082% | 2016–2022 | unmapped | — | `egif-record:2016370056` |
| 299 | — | 13 | 0.002010% | 2016–2023 | unmapped | — | `egif-record:2016170046` |
| 300 | — | 32 | 0.004947% | 2016–2023 | unmapped | — | `egif-record:2016100251` |
| 301 | — | 13 | 0.002010% | 2016–2022 | unmapped | — | `egif-record:2016170077` |
| 302 | — | 9 | 0.001391% | 2016–2023 | unmapped | — | `egif-record:2016450758` |
| 303 | — | 12 | 0.001855% | 2016–2022 | unmapped | — | `egif-record:2016070112` |
| 310 | Causa: Otras causas por ferrocarril (sin especificar) | 2,508 | 0.387703% | 1968–2023 | documented | accidental | `egif-record:1968031145` |
| 311 | — | 192 | 0.029681% | 2016–2023 | unmapped | — | `egif-record:2016020138` |
| 312 | — | 40 | 0.006183% | 2016–2023 | unmapped | — | `egif-record:2016050045` |
| 320 | Causa: Otras causas por líneas eléctricas (sin especificar) | 5,960 | 0.921336% | 1968–2023 | documented | accidental | `egif-record:1968030527` |
| 321 | — | 26 | 0.004019% | 2016–2023 | unmapped | — | `egif-record:2016170045` |
| 322 | — | 612 | 0.094607% | 2016–2023 | unmapped | — | `egif-record:2016020230` |
| 323 | — | 369 | 0.057042% | 2016–2023 | unmapped | — | `egif-record:2016020157` |
| 324 | — | 335 | 0.051786% | 2016–2023 | unmapped | — | `egif-record:2016050115` |
| 325 | — | 57 | 0.008811% | 2016–2023 | unmapped | — | `egif-record:2016080218` |
| 326 | — | 161 | 0.024888% | 2016–2023 | unmapped | — | `egif-record:2016060098` |
| 327 | — | 23 | 0.003555% | 2016–2023 | unmapped | — | `egif-record:2016090050` |
| 328 | — | 8 | 0.001237% | 2017–2023 | unmapped | — | `egif-record:2017190195` |
| 330 | Causa: Mot. y Maq. (s.e.) | 5,708 | 0.882380% | 1968–2023 | documented | accidental | `egif-record:1968050969` |
| 331 | Causa: Maquinaria (cosechadoras) | 1,887 | 0.291705% | 2005–2023 | unmapped | — | `egif-record:2005010016` |
| 332 | — | 121 | 0.018705% | 2016–2023 | unmapped | — | `egif-record:2016090059` |
| 333 | — | 21 | 0.003246% | 2017–2022 | unmapped | — | `egif-record:2017130168` |
| 334 | Causa: Escapes de vehículos (ligeros y pesados) | 1,304 | 0.201581% | 2005–2023 | unmapped | — | `egif-record:2005040091` |
| 335 | — | 67 | 0.010357% | 2016–2023 | unmapped | — | `egif-record:2016080052` |
| 336 | Causa: Accidentes de vehículos (incendios fortuitos, accidentes de tráfico, etc.) | 1,079 | 0.166799% | 2005–2023 | unmapped | — | `egif-record:2005050138` |
| 337 | — | 58 | 0.008966% | 2016–2023 | unmapped | — | `egif-record:2016100055` |
| 340 | Causa: Otras causas en actividades militares (sin especificar) | 498 | 0.076984% | 1968–2022 | documented | accidental | `egif-record:1968250279` |
| 341 | — | 37 | 0.005720% | 2016–2023 | unmapped | — | `egif-record:2016190133` |
| 342 | — | 4 | 0.000618% | 2016–2022 | unmapped | — | `egif-record:2016500075` |
| 350 | — | 129 | 0.019942% | 2016–2023 | unmapped | — | `egif-record:2016060059` |
| 351 | — | 186 | 0.028753% | 2016–2023 | unmapped | — | `egif-record:2016010016` |
| 352 | — | 2 | 0.000309% | 2022–2023 | unmapped | — | `egif-record:2022240214` |
| 353 | — | 15 | 0.002319% | 2016–2022 | unmapped | — | `egif-record:2016050033` |
| 354 | — | 97 | 0.014995% | 2016–2023 | unmapped | — | `egif-record:2016100044` |
| 355 | — | 25 | 0.003865% | 2016–2023 | unmapped | — | `egif-record:2016100096` |
| 356 | — | 10 | 0.001546% | 2020–2023 | unmapped | — | `egif-record:2020210012` |
| 360 | — | 32 | 0.004947% | 2016–2023 | unmapped | — | `egif-record:2016340072` |
| 361 | — | 268 | 0.041429% | 2016–2023 | unmapped | — | `egif-record:2016020108` |
| 362 | — | 84 | 0.012985% | 2016–2023 | unmapped | — | `egif-record:2016030052` |
| 363 | — | 142 | 0.021951% | 2016–2023 | unmapped | — | `egif-record:2016040011` |
| 364 | — | 58 | 0.008966% | 2016–2023 | unmapped | — | `egif-record:2016030075` |
| 365 | — | 3 | 0.000464% | 2019–2022 | unmapped | — | `egif-record:2019490199` |
| 370 | — | 38 | 0.005874% | 2016–2023 | unmapped | — | `egif-record:2016080033` |
| 371 | — | 46 | 0.007111% | 2016–2023 | unmapped | — | `egif-record:2016100333` |
| 372 | — | 61 | 0.009430% | 2016–2023 | unmapped | — | `egif-record:2016330060` |
| 399 | Causa: Otras causas no intencionales (conocidas) | 2,259 | 0.349211% | 2005–2023 | unmapped | — | `egif-record:2005010026` |
| 400 | Causa: Intencionado | 335,852 | 51.918187% | 1968–2023 | documented | intentional | `egif-record:1968021332` |
| 500 | Causa: Desconocida | 139,963 | 21.636391% | 1968–2023 | documented | unknown | `egif-record:1968021570` |
| 600 | Causa: Reproducido | 7,691 | 1.188925% | 1998–2023 | documented | rekindle | `egif-record:1998030058` |

## Campos secundarios

El agregado nacional permite inventariar sus valores, pero no conserva la asociación registro a registro con un código `idcausa`; por tanto, no se presenta una relación causal inferida.

| Campo | Presente | Valores distintos | Primero–último |
|---|---:|---:|---|
| `pif_causa.causaotros` | 545 | 426 | 2016–2023 |
| `pif_causa.diastormenta` | 60,464 | 41 | 2001–2023 |
| `pif_causa.idautorizacionactividad` | 67,905 | 4 | 2016–2023 |
| `pif_causa.idcausante` | 646,887 | 2 | 1968–2023 |
| `pif_causa.idcertidumbrecausa` | 646,887 | 2 | 1968–2023 |
| `pif_causa.idclasedia` | 646,887 | 4 | 1968–2023 |
| `pif_causa.idgradoresponsabilidad` | 67,905 | 5 | 2016–2023 |
| `pif_causa.idinvestigacioncausa` | 67,905 | 3 | 2016–2023 |
| `pif_causa.idmotivacion` | 335,853 | 31 | 1968–2023 |
| `pif_causa.motivacionotros` | 3,679 | 710 | 2016–2023 |

## Documentación local reutilizada

- `data/raw/egif/gva/1968_1992/dictionaries/causes.sparql.json`: snapshot del diccionario público enlazado IEPNB/EGIF. Aporta etiqueta literal para 35 de los 87 códigos observados, pero no versiona el significado por formulario o año.
- `config/egif-web.json`: conserva 15 mappings exactos ya documentados para el mismo campo `idcausa`. Este dossier los reproduce como metadatos y no añade ninguno.
- `CV_3_2_EGIF_AUDIT.md` y `ES_4B1_EGIF_NATIONAL_NORMALIZER.md`: documentan la procedencia y la conservación de la causa fuente, no una ontología nacional definitiva.

## DOCUMENTATION_GAPS

Cada código siguiente sigue sin mapping canónico. La pregunta común es confirmar su significado literal y su vigencia por régimen; tener una etiqueta contemporánea no autoriza por sí solo una equivalencia canónica histórica.

- `211` — 2,608 registros, 2005–2023, Causa: Quemas de rastrojos. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `212` — 4,188 registros, 2005–2023, Causa: Quema agrícola (restos poda). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `213` — 337 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `214` — 156 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `215` — 31 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `216` — 588 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `221` — 1,620 registros, 2005–2023, Causa: Quema de matorral. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `222` — 665 registros, 2005–2023, Causa: Quema de herbáceas. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `231` — 1,293 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `241` — 529 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `242` — 52 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `243` — 113 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `244` — 344 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `261` — 267 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `262` — 518 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `270` — 2,045 registros, 1997–2023, Causa: Escape de vertedero. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `280` — 4,589 registros, 1989–2023, Causa: Otras quemas de limpieza (sin especificar). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `281` — 258 registros, 2005–2023, Causa: Limpieza de vegetación próxima a edificaciones. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `282` — 498 registros, 2005–2023, Causa: Limpieza de accesos (pistas, caminos , sendas, etc). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `283` — 98 registros, 2005–2023, Causa: Limpieza de vegetación para control de animales nocivos (plagas, conejos, etc.). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `284` — 1,810 registros, 2005–2023, Causa: Limpieza de lindes y bordes de finca. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `285` — 258 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `286` — 909 registros, 2005–2023, Causa: Limpieza de infraestructuras de riego (acequias,cavas, etc.). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `291` — 271 registros, 2005–2023, Causa: Apicultura. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `292` — 730 registros, 2005–2023, Causa: Fuegos artificiales (petardos, cohetes,etc.). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `293` — 19 registros, 2005–2022, Causa: Globos aerostáticos. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `294` — 1,899 registros, 2005–2023, Causa: Gamberradas, juegos de niños (quema de pelusa de chopo, etc). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `295` — 240 registros, 2005–2023, Causa: Quema de restos de poda o jardinería en urbanizaciones. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `296` — 7 registros, 2017–2022, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `297` — 41 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `298` — 7 registros, 2016–2022, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `299` — 13 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `300` — 32 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `301` — 13 registros, 2016–2022, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `302` — 9 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `303` — 12 registros, 2016–2022, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `311` — 192 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `312` — 40 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `321` — 26 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `322` — 612 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `323` — 369 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `324` — 335 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `325` — 57 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `326` — 161 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `327` — 23 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `328` — 8 registros, 2017–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `331` — 1,887 registros, 2005–2023, Causa: Maquinaria (cosechadoras). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `332` — 121 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `333` — 21 registros, 2017–2022, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `334` — 1,304 registros, 2005–2023, Causa: Escapes de vehículos (ligeros y pesados). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `335` — 67 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `336` — 1,079 registros, 2005–2023, Causa: Accidentes de vehículos (incendios fortuitos, accidentes de tráfico, etc.). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `337` — 58 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `341` — 37 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `342` — 4 registros, 2016–2022, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `350` — 129 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `351` — 186 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `352` — 2 registros, 2022–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `353` — 15 registros, 2016–2022, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `354` — 97 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `355` — 25 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `356` — 10 registros, 2020–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `360` — 32 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `361` — 268 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `362` — 84 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `363` — 142 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `364` — 58 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `365` — 3 registros, 2019–2022, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `370` — 38 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `371` — 46 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `372` — 61 registros, 2016–2023, sin etiqueta local. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
- `399` — 2,259 registros, 2005–2023, Causa: Otras causas no intencionales (conocidas). Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.
