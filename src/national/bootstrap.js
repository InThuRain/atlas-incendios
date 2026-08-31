import "./runtime-config.js";

const config = globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__;

function loadClassicScript(url) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = url; script.async = false;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`No se pudo cargar dependencia de mapa: ${url}`));
    document.head.append(script);
  });
}

async function bootstrap() {
  if (!globalThis.maplibregl) await loadClassicScript(config.maplibre_script);
  // En D2 se mantiene el runtime ES-4C como módulo compartido y congelado:
  // el nuevo entrypoint no depende de su HTML ni de su bootstrap experimental.
  await import(new URL(config.runtime_entry, import.meta.url));
}

bootstrap().catch((error) => {
  const target = document.querySelector("#national-bootstrap-error");
  if (target) target.textContent = `No se pudo iniciar el Atlas nacional: ${error.message}`;
});
