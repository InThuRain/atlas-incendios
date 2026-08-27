# ES-4B4B2A — Recuperación del diccionario oficial de causas EGIF

## Resultado

No se ha localizado la tabla Access `CodXXXXX` que relaciona directamente `pif_causa.idcausa` con textos e `IdIdioma`. La documentación oficial confirma que esa tabla existe en la distribución Access, pero los 56 ZIP/XML públicos disponibles contienen únicamente XML de partes.

Sí se ha extraído una recuperación parcial del snapshot oficial IEPNB/EGIF: 35 códigos numéricos con etiqueta literal. No se presenta como la tabla `CodXXXXX`, no contiene `IdIdioma` y su vigencia temporal es `unknown`.

- Códigos EGIF observados en ES-4B4B1: **87**.
- Encontrados exactamente en el diccionario parcial: **35**.
- Sin etiqueta en el diccionario parcial: **52**.
- Códigos con más de una etiqueta en la extracción: **0**.

## Tabla parcial extraída

| Código | Etiqueta fuente literal | Idioma fuente | Vigencia |
|---:|---|---|---|
| 100 | Causa: Rayo | no suministrado | unknown |
| 210 | Causa: Quema agrícola (s.e.) | no suministrado | unknown |
| 211 | Causa: Quemas de rastrojos | no suministrado | unknown |
| 212 | Causa: Quema agrícola (restos poda) | no suministrado | unknown |
| 220 | Causa: Otras quemas ganaderas (sin especificar) | no suministrado | unknown |
| 221 | Causa: Quema de matorral | no suministrado | unknown |
| 222 | Causa: Quema de herbáceas | no suministrado | unknown |
| 230 | Causa: Otras quemas en trabajos forestales (conocidas) | no suministrado | unknown |
| 240 | Causa: Otros tipos de hogueras (conocidas) | no suministrado | unknown |
| 250 | Causa: Fumadores | no suministrado | unknown |
| 260 | Causa: Otros incendios  por quema de basuras (conocidas) | no suministrado | unknown |
| 270 | Causa: Escape de vertedero | no suministrado | unknown |
| 280 | Causa: Otras quemas de limpieza (sin especificar) | no suministrado | unknown |
| 281 | Causa: Limpieza de vegetación próxima a edificaciones | no suministrado | unknown |
| 282 | Causa: Limpieza de accesos (pistas, caminos , sendas, etc) | no suministrado | unknown |
| 283 | Causa: Limpieza de vegetación para control de animales nocivos (plagas, conejos, etc.) | no suministrado | unknown |
| 284 | Causa: Limpieza de lindes y bordes de finca | no suministrado | unknown |
| 286 | Causa: Limpieza de infraestructuras de riego (acequias,cavas, etc.) | no suministrado | unknown |
| 290 | Causa: Otras causas no intencionales (sin determinar) | no suministrado | unknown |
| 291 | Causa: Apicultura | no suministrado | unknown |
| 292 | Causa: Fuegos artificiales (petardos, cohetes,etc.) | no suministrado | unknown |
| 293 | Causa: Globos aerostáticos | no suministrado | unknown |
| 294 | Causa: Gamberradas, juegos de niños (quema de pelusa de chopo, etc) | no suministrado | unknown |
| 295 | Causa: Quema de restos de poda o jardinería en urbanizaciones | no suministrado | unknown |
| 310 | Causa: Otras causas por ferrocarril (sin especificar) | no suministrado | unknown |
| 320 | Causa: Otras causas por líneas eléctricas (sin especificar) | no suministrado | unknown |
| 330 | Causa: Mot. y Maq. (s.e.) | no suministrado | unknown |
| 331 | Causa: Maquinaria (cosechadoras) | no suministrado | unknown |
| 334 | Causa: Escapes de vehículos (ligeros y pesados) | no suministrado | unknown |
| 336 | Causa: Accidentes de vehículos (incendios fortuitos, accidentes de tráfico, etc.) | no suministrado | unknown |
| 340 | Causa: Otras causas en actividades militares (sin especificar) | no suministrado | unknown |
| 399 | Causa: Otras causas no intencionales (conocidas) | no suministrado | unknown |
| 400 | Causa: Intencionado | no suministrado | unknown |
| 500 | Causa: Desconocida | no suministrado | unknown |
| 600 | Causa: Reproducido | no suministrado | unknown |

## Top 10 unmapped de ES-4B4B1

| Código | Frecuencia | Resultado de la tabla parcial | Etiqueta literal |
|---:|---:|---|---|
| 280 | 4,589 | exact_label_found | Causa: Otras quemas de limpieza (sin especificar) |
| 212 | 4,188 | exact_label_found | Causa: Quema agrícola (restos poda) |
| 211 | 2,608 | exact_label_found | Causa: Quemas de rastrojos |
| 399 | 2,259 | exact_label_found | Causa: Otras causas no intencionales (conocidas) |
| 270 | 2,045 | exact_label_found | Causa: Escape de vertedero |
| 294 | 1,899 | exact_label_found | Causa: Gamberradas, juegos de niños (quema de pelusa de chopo, etc) |
| 331 | 1,887 | exact_label_found | Causa: Maquinaria (cosechadoras) |
| 284 | 1,810 | exact_label_found | Causa: Limpieza de lindes y bordes de finca |
| 221 | 1,620 | exact_label_found | Causa: Quema de matorral |
| 334 | 1,304 | exact_label_found | Causa: Escapes de vehículos (ligeros y pesados) |

## Temporalidad

El snapshot IEPNB no aporta fechas de alta, baja o cambio de texto. Por ello ningún texto recuperado se declara automáticamente válido para todos los formularios 1968–2023.

## Consulta propuesta a MITECO

> Asunto: Solicitud de tabla de códigos de causa EGIF (`pif_causa.idcausa`)
>
> Estamos documentando de forma reproducible la serie EGIF 1968–2023. La guía oficial de interpretación indica que las tablas `CodXXXXX` de la base Access relacionan los códigos numéricos con sus textos y que deben filtrarse por `IdIdioma`.
>
> ¿Podrían facilitar o indicar la tabla `CodXXXXX` concreta asociada a `pif_causa.idcausa`, la plantilla Access pública que la contiene y, si existen, versiones históricas/vigencias de los códigos? Necesitamos conservar `id`, `IdIdioma`, texto y fecha o versión aplicable. También agradeceríamos confirmar si la tabla puede reutilizarse y la atribución requerida.

Destinatario propuesto: `bzn-egif@miteco.es` (o el contacto ADCIF que MITECO indique). No se ha enviado ningún correo.
