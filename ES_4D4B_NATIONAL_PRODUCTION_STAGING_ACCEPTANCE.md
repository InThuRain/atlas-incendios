# ES-4D4B — Aceptación de staging nacional

## Estado

`STAGING_DEPLOYMENT_STATUS = FAIL` y
`REMOTE_ACCEPTANCE_STATUS = NOT_RUN`.

El despliegue se detuvo de forma intencional antes de crear el artifact Pages
o cambiar el contenido servido. El motivo es
`ARTIFACT_IDENTITY_MISMATCH` en el contrato de tamaño del artifact D4A.

| Campo | Esperado/aprobado | Observado al extraer |
| --- | ---: | ---: |
| Ficheros | 349 | 349 |
| Bytes declarados en manifest | 500.449.810 | — |
| Bytes físicos | 500.449.810 | 500.449.871 |
| Diferencia | 0 | +61 |
| Content fingerprint | `bbf980…44ee8` | `bbf980…44ee8` |

La huella de contenidos coincide porque, por diseño D4A, excluye
`asset-manifest.json`. Los 61 B aparecen al reescribir el propio manifest con
sus campos finales: el builder calculó `total_bytes` antes de su última
serialización. Por tanto la propiedad declarada no representa el árbol físico
que Pages recibiría. No se ha corregido ni reconstruido silenciosamente el
artifact congelado.

## Auditoría de staging y rollback

- Repositorio permitido: `InThuRain/atlas-incendios-es4c3d4-pages-staging`.
- URL de staging existente: <https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/>.
- `PRE_DEPLOY_STAGING_COMMIT`: `d8e6f84cfeb9597dc0f4327f427912b97ae93c3e`.
- Workflow previo: `.github/workflows/pages-staging.yml`, última ejecución
  correcta `33429628113`.
- Pages del repositorio staging sigue configurado como `workflow`.
- La raíz pública <https://inthurain.github.io/atlas-incendios/> no se ha
  tocado ni se ha desplegado.

## Mecanismo probado

Se añadió solamente al repo staging el commit
`f58eb3f778ccd953c00a127e5d1b6bc8e9d9bde6`
(`Deploy approved national staging artifact`), con un workflow oficial Pages:

`download package → SHA transport → extract → content contract →
configure-pages → upload-pages-artifact → deploy-pages`.

El paquete temporal, marcado como prerelease de staging, no entra en Git:

- release/tag: `es4d4a-national-pages-artifact`;
- asset: `national-pages-staging-d4a.tar.gz`;
- bytes: 136.809.234;
- SHA-256: `52ca395bc0ef9fa5dadec3f62f3b145c36dd6e1560900d80758d4cb9df810ab5`.

La descarga y el SHA de transporte pasaron. La ejecución
[`33516317541`](https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/actions/runs/33516317541)
falló en la validación del contrato de contenido, antes de upload/deploy.
No hay un nuevo deployment remoto ni browser acceptance que atribuir al
artifact D4A.

## Lo que no se ejecutó

Quedan `NOT_RUN`: HEAD/Range remoto, smokes España/Galicia/Cangas/GVA/Elx,
permalinks, 2024AL0005, recarga, móvil, cabeceras de caché y auditoría de
dominios. Ejecutarlos contra el staging anterior no demostraría el artifact
D4A y sería evidencia inválida.

## Acción necesaria

No puede continuar D4B con el artifact congelado. Hace falta una decisión
explícita para reabrir **ES-4D4A** y corregir el cálculo estable de
`asset-manifest.json`, reconstruir localmente, volver a aprobar los nuevos
bytes/package SHA y revalidar identidad. Solo después podrá relanzarse el
workflow D4B y realizar la aceptación real.

El release asset y el workflow de staging se conservan como evidencia y como
mecanismo reproducible; no se borran en esta fase.
