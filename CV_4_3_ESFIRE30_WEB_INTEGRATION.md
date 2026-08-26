# CV-4.3 — Integración web local de ESFire30 1985–1992

Fecha de cierre técnico local: 25/08/2026. **No publicado y sin bundle público
nuevo.**

## 1. Resultado

Se han preparado e integrado localmente los **710 perímetros ESFire30** que
intersectan el País Valencià en 1985–1992 como una fuente independiente de
calidad `B_DOCUMENTED_REMOTE_SENSING`.

La integración no convierte esos polígonos en incendios administrativos, no
los asigna a partes EGIF y no modifica `geometry=null` en los 9.175 registros
EGIF. El perfil público candidato queda formado por EGIF + ESFire30 + ICV +
EFFIS y continúa excluyendo SIGIF; el sitio desplegado y `public-data-v4`
permanecen intactos.

## 2. Pipeline e identidad

El recorrido reproducible es:

```text
ESFire30 Causes v1 ZIP (raw, ignorado)
  -> normalizado 1985–1992 (JSONL, ignorado)
  -> tres GeoJSON web por LOD (ignorados)
  -> manifest ESFire30
  -> manifest de ejecución development/public candidato
```

`scripts/build_esfire30_frontend_assets.py` valida antes de transformar:

- ZIP v1: SHA-256
  `150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8`;
- los ocho `.prj` pre-1993: contenido ED50/UTM 30N y checksum esperado;
- rejilla IGN `es_ign_SPED2ETV2.tif`: checksum fijado;
- operación PROJ seleccionada: debe contener `ED50 to WGS 84 (41)`;
- recuento final, validez y unicidad: exactamente 710.

La identidad no depende de la posición de una feature dentro del SHP:

- `source_feature_fingerprint_sha256`: SHA-256 de año, atributos originales
  canónicos y checksum de geometría original;
- `source_record_id` versionado:
  `esfire30:v1:record:sha256:<fingerprint>`;
- `entity_id` estable para web/permalink:
  `esfire30:record:sha256:<fingerprint>`;
- `geometry_id`:
  `esfire30:geometry:sha256:<checksum-geometría-original>`;
- `source_index` se conserva solo como procedencia.

Una actualización futura no se enlazará por índice: deberá recalcular estos
fingerprints y auditar altas, bajas y cambios. El normalizado conserva
atributos y geometría original EPSG:23030, geometría derivada EPSG:4326,
relaciones espaciales y procedencia. El asset web elimina los atributos fuente
no necesarios.

El ZIP fuente mide 93.127.811 bytes. El normalizado JSONL mide 8.250.077 bytes
(SHA-256 `4361828d0018d594a76e337b038f7002c4d7ba29f9b8039429f40f91ce5e6ef3`).
Los tres derivados web suman 6.825.667 bytes raw / 1.588.427 bytes gzip, aunque
el navegador solo carga el nivel correspondiente al zoom.

## 3. CRS y transformación

Se aplica exclusivamente:

```text
EPSG:23030 (ED50 / UTM 30N)
  -> Inverse of UTM zone 30N + ED50 to WGS 84 (41) + axis order change (2D)
  -> EPSG:4326
```

La operación usa la rejilla oficial IGN fijada en CV-4.2 y declara precisión
geodésica de 1 m. Esa cifra **no** describe la precisión temática Landsat. Si
falta la rejilla, cambia su checksum, cambia un `.prj` o PROJ elige otra
operación, el build falla; no existe fallback silencioso.

## 4. Niveles de detalle

Antes de simplificar había 84.894 vértices. Todos los niveles conservan 710
geometrías válidas y ninguna geometría vacía o colapsada.

| Nivel | Tolerancia | Vértices | Reducción | Error área mediano / p95 / máximo | Raw | Gzip |
|---|---:|---:|---:|---:|---:|---:|
| local | 0 m | 84.894 | 0 % | 0 / 0 / 0 | 2.718.495 B | 651.989 B |
| regional | 20 m | 62.782 | 26,047 % | 0,321 % / 1,711 % / 3,571 % | 2.239.127 B | 520.040 B |
| overview | 30 m | 45.670 | 46,204 % | 0,903 % / 4,762 % / 10,169 % | 1.868.045 B | 416.398 B |

El error máximo de los polígonos menores de 10 ha coincide con 3,571 % en
regional y 10,169 % en overview. Ninguno desaparece. Se eligen 20/30 m frente
a tolerancias mayores para proteger los perímetros pequeños; local conserva la
geometría Landsat sin simplificar.

Checksums finales:

- local: `2af1d6f0997c30344806ef90311e1bbee878fb6a46fdce07250c8425e0d87335`;
- regional: `fed00613de4c0f3c29e05235649de21f3c14cc7ed1c97ac3643aa8c87b7b354e`;
- overview: `894af3c057b6cff5978e48efb7d4273d8d9d5fdf8d9b8c0f1de7791ff5c5646e`.

## 5. Reconciliación y superficie

| Año | Polígonos |
|---:|---:|
| 1985 | 127 |
| 1986 | 63 |
| 1987 | 19 |
| 1988 | 25 |
| 1989 | 23 |
| 1990 | 100 |
| 1991 | 171 |
| 1992 | 182 |
| **Total** | **710** |

Provincia principal derivada por mayor área de intersección: Alicante 195,
Castellón 206 y Valencia 309. Esta asignación reconcilia CV-4.2, pero no recorta
los 29 polígonos que intersectan más de una provincia.

La superficie fuente suma **127.083,78 ha**; mediana 16,11 ha, p95 483,3765 ha,
mínimo 5,04 ha y máximo 13.663,08 ha. Hay 36 perímetros con superficie
cartografiada ≥500 ha. La interfaz los denomina así: nunca los llama GIF.

## 6. Municipios y provincias

Las relaciones territoriales se derivan por intersección de área positiva con
el catálogo oficial de 542 municipios ya usado por el proyecto:

- 1.110 relaciones perímetro→municipio;
- 268 municipios canónicos representados;
- 251 perímetros intersectan más de un municipio;
- 29 intersectan más de una provincia;
- ningún polígono se recorta o duplica por territorio.

Los filtros de provincia comprueban todas las provincias intersectadas, no solo
la principal. Los filtros de municipio usan todas las relaciones. Los nombres
se presentan como “municipios intersectados” y no como municipio administrativo
del incendio; `primary_province` se rotula siempre como derivada.

## 7. Interfaz y semántica

ESFire30 dispone de control de fuente, leyenda y estilo propios: borde punteado,
tono histórico y relleno temporal, distinto del sólido ICV y del discontinuo
EFFIS. La ficha muestra como información principal solo año y superficie
cartografiada. El bloque técnico conserva metodología Landsat 30 m, calidad B,
IDs, versión, checksum/procedencia y relaciones espaciales derivadas.

El aviso visible dice que es un área quemada detectada con Landsat, no un
perímetro oficial, una geometría EGIF o un episodio administrativo confirmado.
No se expone ninguna causa ESFire30 ni se reutilizan sus inferencias EGIF.

## 8. Timeline, histograma y métricas

El timeline permanece en 1968–2026. Entre 1985 y 1992 coexisten dos canales:

- EGIF: partes administrativos, superficie forestal declarada y GIF;
- ESFire30: perímetros Landsat, superficie cartografiada y perímetros ≥500 ha.

El histograma muestra franjas diferenciadas por fuente. Para evitar una suma
semánticamente falsa, la altura de cada año usa el **máximo** de los recuentos
por fuente, no la suma; el tooltip enumera cada cifra y explica la regla. Las
métricas permanecen en tarjetas separadas y no suman superficies EGIF +
ESFire30.

El filtro de superficie mínima sí se aplica a la superficie cartografiada
ESFire30. El filtro “solo GIF” y el filtro de causa la excluyen, porque ESFire30
no aporta clasificación GIF administrativa ni una causa comparable segura.

## 9. Historia de un lugar y relaciones EGIF

La consulta puntual añade una sección independiente “Teledetección histórica
ESFire30”. Solo cuenta polígonos que contienen geométricamente el punto. No
incorpora partes EGIF por municipio/cuadrícula y no afirma cuántas veces ardió
un punto.

Los diagnósticos CV-4.2 permanecen fuera de la UX normal: 3 candidatos fuertes,
34 posibles, 3 débiles, 140 sin candidato y 0 confirmados entre los 180 partes
EGIF GIF. No se genera asset web de relaciones ni se enlaza `entity_id`.

## 10. Casos de control

- Sot de Chera, 18/05/1986: parte EGIF de 877 ha y candidato ESFire30 de
  821,07 ha permanecen separados; el enlace diagnóstico sigue siendo fuerte,
  no confirmado.
- Yátova y Chiva, 1991: sus candidatos fuertes se mantienen solo en la
  auditoría CV-4.2.
- Sot de Chera, 31/08/1992: la diferencia frente a polígonos pequeños no se
  corrige ni se fuerza.
- Marines–Altura, 1992: no se resuelve la identidad multiparte; los candidatos
  posibles/débiles no aparecen en la interfaz.

## 11. Perfiles y publicación

`config/sources-gva.json` marca ESFire30 `publishable=true` bajo CC BY 4.0. El
perfil development candidato contiene EGIF + ESFire30 + ICV + SIGIF + EFFIS;
el public candidato contiene EGIF + ESFire30 + ICV + EFFIS y rechaza SIGIF.

El guard local pasó con `all_included_sources_publishable=true`. Un sitio
candidato autocontenido se montó y validó con 44 assets de datos y 83.979.085
bytes incluyendo el manifest. No se creó `public-data-v5`, no se modificó
`config/public-data-bundle.json`, no se activó el workflow y GitHub Pages sigue
sirviendo `public-data-v4` sin ESFire30.

## 12. Rendimiento

Chrome headless, tres repeticiones, servidor local sin compresión; medianas:

| Escenario public | Assets | Gzip estimado | App | Carga | Render | Heap |
|---|---:|---:|---:|---:|---:|---:|
| escritorio completo sin ESFire30 | 15 | 2.686.126 B | 693,1 ms | 270,2 ms | 329,1 ms | 190,3 MiB |
| escritorio completo con ESFire30 | 16 | 3.102.524 B | 835,0 ms | 282,2 ms | 357,5 ms | 196,2 MiB |
| móvil completo sin ESFire30 | 15 | 2.686.126 B | 677,4 ms | 239,7 ms | 334,6 ms | 182,7 MiB |
| móvil completo con ESFire30 | 16 | 3.102.524 B | 808,0 ms | 261,6 ms | 361,4 ms | 179,9 MiB |

Coste determinista inicial: una petición, 1.868.045 bytes raw y 416.398 bytes
gzip overview. Parseo ESFire30: 7,6 ms escritorio / 6,9 ms móvil. El heap móvil
completo varía por GC y no permite interpretar la diferencia negativa como un
ahorro; el ensayo histórico aislado pasa de 15,6 a 32,8 MiB al añadir la capa.

El arranque mediano sigue por debajo de un segundo y no hubo bloqueos en móvil
emulado. Por ello ESFire30 queda activo por defecto en ambos perfiles
candidatos. Sigue pendiente comprobar un dispositivo físico de gama baja.

## 13. Validación ejecutada

- 47 tests unitarios: OK;
- build ESFire30 completo + `--check`: reproducible;
- validadores ICV, EGIF y recent: OK;
- smoke development bajo `/atlas-incendios/`: 47 escenarios, OK;
- smoke public candidato: 58 escenarios, OK, incluidos 1984/1985/1991 y los
  casos nominales de Sot de Chera, Yátova, Chiva y Marines–Altura;
- permalink ESFire30: restaura entidad, `geometry_id`, resaltado, ficha y popup;
- filtros municipal/provincial multirrelación: OK;
- Historia de un lugar separada: OK;
- public candidato sin SIGIF/candidatos y rechazo fail-closed de SIGIF: OK;
- sitio public candidato: 44 assets, integridad y atribuciones, OK;
- escritorio y móvil emulado: OK.

## 14. Licencia y atribución

Zenodo declara CC BY 4.0. Se conserva la fórmula:

> ESFire30 Causes, Ochoa, Chuvieco, Rodrigues y Franquesa (2026), versión v1,
> CC BY 4.0, DOI 10.5281/zenodo.18449006. Datos transformados para el Atlas
> mediante selección territorial, reproyección a EPSG:4326, selección de
> atributos y, cuando proceda, simplificación geométrica.

El vector puede redistribuirse y transformarse con atribución y aviso de
cambios. El Atlas no redistribuye las escenas Landsat de origen.

## 15. Consulta breve a autores

El borrador completo sigue en `CV_4_2_CONTACT_PACKET.md`. Conviene solicitar:

1. confirmación escrita de EPSG:23030 y de las erratas EPSG:25830/“30 km”;
2. semántica exacta de feature y posibilidad de varias manchas por episodio;
3. identificador estable o regla de correspondencia entre versiones;
4. ventanas temporales/sensores por año y documentación del producto base;
5. previsión de versión corregida o changelog.

La consulta mejora metadatos futuros, pero no es una condición de licencia para
el derivado candidato ya auditado.

## 16. Decisiones pendientes y recomendación CV-4.4

No hay bloqueo técnico para preparar la publicación. CV-4.4 debería ser una
fase exclusivamente de empaquetado y despliegue:

1. revisar visualmente la capa local;
2. decidir si se espera o no la confirmación técnica de los autores;
3. generar un bundle inmutable `public-data-v5` que añada los tres assets y su
   manifest, sin modificar `public-data-v4`;
4. verificar dos construcciones idénticas y fijar SHA-256;
5. ejecutar guard, suite, sitio candidato y pruebas reales tras desplegar;
6. actualizar documentación de publicación solo después de comprobar la URL.

No debe incluir SIGIF, candidatos EGIF–ESFire30, raw, processed ni benchmarks.
