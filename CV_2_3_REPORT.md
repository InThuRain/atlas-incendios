# CV-2.3 — Integración local de datos recientes en el visor

Fecha de ejecución: 19 de agosto de 2026.

## Resultado

El visor cubre 1993–2026 sin un máximo de año codificado en el componente
temporal. El perfil local `development` mantiene tres capas conceptuales y
técnicas separadas:

- ICV 1993–2024: incendios identificados y perímetros oficiales consolidados A;
- SIGIF 2025–2026: registros administrativos provisionales representados como
  puntos de inicio;
- EFFIS 2025–2026: perímetros satelitales provisionales B.

No se crea una identidad común SIGIF–EFFIS. Los candidatos conservan
`link_status=candidate`, score y métricas. La interfaz no suma superficies de
fuentes distintas ni llama “incendios” a la colección EFFIS.

## Build y publicación

`config/sources-gva.json` es el catálogo único de autoridad, estado y permiso.
Los comandos reproducibles son:

```bash
python3 scripts/build_recent_frontend_assets.py
python3 scripts/build_frontend_profile.py --profile development
python3 scripts/build_frontend_profile.py --profile public
python3 scripts/validate_recent_frontend_assets.py
```

`development` referencia ICV + SIGIF + EFFIS locales. `public` contiene solo
EFFIS. Forzar `--profile public --include-source sigif` o `icv` termina con
código distinto de cero. El build no publica archivos.

## Assets recientes

Se generan seis assets de datos, además del manifiesto reciente y el manifiesto
de ejecución:

| Asset | Registros | Bytes | gzip |
|---|---:|---:|---:|
| SIGIF 2025 | 281 | 264.790 | 36.626 |
| SIGIF 2026 | 143 | 135.103 | 18.940 |
| EFFIS 2025 | 9 | 36.694 | 10.977 |
| EFFIS 2026 | 16 | 216.623 | 65.865 |
| candidatos strong/possible | 11 | 11.593 | 1.635 |
| candidatos weak (solo debug) | 42 | 43.683 | 3.407 |
| **Total** |  | **708.486** | **137.450** |

Los GeoJSON EFFIS no se simplifican. Los atributos web son mínimos y no
incluyen `original_attributes`. Todos estos archivos permanecen bajo
`data/web/gva/`, ignorados por Git.

## Interfaz y cobertura

El arranque predeterminado es 2026. La cobertura visible procede del manifiesto:
SIGIF termina el 30/06/2026 y `coverage_complete=false`; EFFIS muestra la fecha
de adquisición 19/08/2026. Para 2025 se indica que el periodo observado llega a
31/12/2025, aunque la colección sigue siendo provisional.

El color conserva un gradiente temporal estable entre el primer y el último año
del manifiesto (azul antiguo → naranja reciente). La fuente se distingue además
por geometría y trazo, no solo por color: polígono sólido ICV, punto SIGIF con
doble contorno y polígono EFFIS discontinuo. Hay filtros por fuente. Las métricas separan incendios/perímetros/área/GIF ICV, registros/área/GIF
SIGIF y perímetros/área cartografiada EFFIS.

“Historia de un lugar” agrupa ICV por `fire_id`, cuenta por separado los
perímetros EFFIS y solo presenta puntos SIGIF próximos con un radio explícito de
5 km.

## Casos de aceptación

- Ibi / Sant Pasqual: se muestran el punto SIGIF de 18/07/2025 y el perímetro
  EFFIS 275862 como elementos independientes. La ficha muestra candidato fuerte,
  score 90/100, 0 días y 13,184 m; no afirma identidad.
- Nules (EFFIS 570518) y Tírig (EFFIS 612812): son visibles en 2026 aunque sus
  fechas sean posteriores al corte SIGIF. La ficha explica que la ausencia de
  registro correspondiente se refiere al snapshot SIGIF incompleto y no a una
  afirmación de inexistencia.
- Los 42 candidatos weak no se descargan ni aparecen por defecto. Se reservan
  para `quality_debug=1`.

## Rendimiento

Medición Chrome headless local, una ejecución con reloj real (sin simular
latencia de red):

| Escenario | Assets | Carga | Render | Heap | gzip datos estimado |
|---|---:|---:|---:|---:|---:|
| Escritorio inicial 2026 | 2 | 13,4 ms | 15,4 ms | 7,20 MiB | 86.440 B |
| Escritorio ICV 2024 | 3 | 69,8 ms | 28,0 ms | 33,75 MiB | 908.710 B |
| Escritorio 1993–2026 | 16 | 230,7 ms | 292,6 ms | 162,90 MiB | 3.111.676 B |
| Móvil 390×844, inicial 2026 | 2 | 12,6 ms | 13,3 ms | 6,91 MiB | 86.440 B |

El arranque reciente hace cuatro peticiones de datos: manifiesto de ejecución,
dos GeoJSON 2026 y candidatos visibles. No carga `fires.json`, geometrías ICV ni
candidatos weak. Frente al arranque CV-1.5 de 2024 (cinco peticiones, 33,1 MiB
de heap y 908.710 B gzip estimados), el nuevo arranque reduce transferencia y
memoria porque los atributos ICV pasan a carga diferida. La vista completa sigue
siendo deliberadamente una operación pesada.

Al seleccionar solo 2024 no se descargan candidatos ni assets recientes: se
mantienen los mismos 908.710 B gzip estimados de CV-1.5. En esta máquina el heap
subió aproximadamente 0,65 MiB (33,1 → 33,75 MiB) y el render 6,1 ms (21,9 →
28,0 ms); son incrementos pequeños frente al coste de las geometrías y deben
interpretarse como benchmark local, no como garantía para todo dispositivo.

## Validación

Las cifras son medianas de tres ejecuciones. `run_smoke.py` pasó 18 escenarios bajo `/atlas-incendios/`, incluidos 2024,
2025, 2026, provincias, piloto, zoom, filtros de fuente, Ibi, Nules, Tírig,
consulta puntual EFFIS, `2024AL0005`, geometría reutilizada y móvil. Los
validadores ICV y reciente pasaron. `run_profile_smoke.py` arrancó el perfil
público con dos peticiones y solo 16 EFFIS 2026, y comprobó el rechazo de ICV.
La suite `unittest` pasó sus cuatro pruebas en el entorno reproducible creado
desde `requirements-dev.txt`, con pyproj 3.5.0 y Shapely 2.0.7.

No se hizo commit ni publicación.
