import { resolveAssetConfig } from "./asset-config.mjs";

// Test/deploy puede inyectar una configuración antes de este módulo. No se
// aceptan query params de staging ni URLs remotas como configuración de runtime.
globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__ = resolveAssetConfig(
  globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__ || {},
);
