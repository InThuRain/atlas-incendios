# Contexto del proyecto

## Visión

Crear una herramienta pública y visual para explorar más de medio siglo de incendios forestales en España.

La pregunta principal no es solo “¿dónde hubo incendios?”, sino también:

- ¿qué zonas han ardido varias veces?
- ¿cuándo ardieron?
- ¿qué superficie se quemó?
- ¿qué causas aparecen registradas?
- ¿qué grandes incendios han condicionado el paisaje actual?
- ¿qué sabemos con precisión y qué información tiene incertidumbre?

## Origen del proyecto

El proyecto comenzó con una necesidad concreta: disponer de un histórico de incendios de los últimos ~50 años en Serra de Mariola, Font Roja y alrededores, viendo el **perímetro de cada incendio sobre un mapa**.

Durante la exploración se comprobó que la Generalitat Valenciana publica numerosos perímetros anuales de incendios en servicios ArcGIS, especialmente útiles para 1993–2024.

A partir de ahí se decidió ampliar el concepto a toda España.

## Conceptos clave

### Incendio

Registro de un evento de incendio forestal con atributos estadísticos.

Ejemplos:

- identificador;
- fecha de inicio/extinción;
- municipio/provincia/CCAA;
- superficie;
- causa;
- daños;
- fuente estadística.

### Geometría

Representación espacial asociada a un incendio.

Puede ser:

- polígono oficial;
- polígono de teledetección;
- reconstrucción histórica;
- punto;
- geometría administrativa;
- inexistente.

La relación incendio-geometría no debe suponerse 1:1.

## Horizonte temporal

Objetivo inicial nacional: desde **1968**, coincidiendo con el inicio histórico de EGIF, hasta la actualidad.

Para el área piloto se planteó inicialmente estudiar aproximadamente los últimos 50 años, incluyendo el periodo anterior a 1993 mediante EGIF, documentación histórica y otras fuentes.

## Funcionalidades objetivo

### Exploración básica

- mapa pan/zoom;
- filtro por fechas;
- filtro por superficie;
- filtro por causa;
- filtro territorial;
- GIF >= 500 ha;
- selección de incendio;
- ficha detallada.

### Recurrencia

- pulsar un punto y saber cuántas veces ha ardido;
- enumerar años e incendios asociados;
- mapa de recurrencia;
- superficie que ha ardido 1, 2, 3 o más veces.

### Historia de un territorio

Seleccionar o dibujar un área y obtener:

- número de incendios;
- superficie total declarada;
- superficie única afectada;
- superficie afectada repetidamente;
- mayor incendio;
- último incendio;
- años desde el último incendio;
- distribución por causas;
- evolución anual.

### Comparación temporal

Comparar periodos, por ejemplo:

- 1970–1995 vs 1996–2025;
- dos décadas;
- antes/después de una fecha.

### Calidad y procedencia

Mostrar en la ficha:

- fuente estadística;
- fuente de geometría;
- calidad geométrica A/B/C/D;
- fecha de adquisición;
- observaciones y limitaciones.

## Área piloto como banco de pruebas

Mariola–Font Roja debe seguir siendo el banco de pruebas para nuevas funciones antes de llevarlas a España entera.

Orden deseable:

1. piloto local robusto;
2. Comunitat Valenciana;
3. España.
