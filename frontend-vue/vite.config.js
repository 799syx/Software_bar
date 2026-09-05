import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import ts from "typescript";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = dirname(fileURLToPath(import.meta.url));
const workspaceRoot = resolve(frontendRoot, "..");

function inlineEnvForRestrictedShell(command, mode) {
  const env = {
    ...loadEnv(mode, workspaceRoot, ""),
    ...loadEnv(mode, frontendRoot, "")
  };
  const envMap = {
    MODE: mode,
    BASE_URL: "/",
    DEV: command !== "build",
    PROD: command === "build",
    SSR: false
  };
  for (const [key, value] of Object.entries(env)) {
    if (key.startsWith("VITE_")) envMap[key] = value;
  }
  const nodeEnv = JSON.stringify(process.env.NODE_ENV || (command === "build" ? "production" : mode));

  return {
    name: "inline-env-for-restricted-shell",
    enforce: "pre",
    transform(code, id) {
      if (id.includes("\0")) return null;

      let next = code;
      next = next.replaceAll("__VUE_OPTIONS_API__", "true");
      next = next.replaceAll("__VUE_PROD_DEVTOOLS__", "false");
      next = next.replaceAll("__VUE_PROD_HYDRATION_MISMATCH_DETAILS__", "false");
      next = next.replaceAll("process.env.NODE_ENV", nodeEnv);
      next = next.replaceAll("global.process.env.NODE_ENV", nodeEnv);
      next = next.replaceAll("globalThis.process.env.NODE_ENV", nodeEnv);
      next = next.replaceAll("import.meta.hot", "undefined");
      next = next.replace(/import\.meta\.env\.([A-Z0-9_]+)/g, (_, key) => {
        if (Object.prototype.hasOwnProperty.call(envMap, key)) {
          return JSON.stringify(envMap[key]);
        }
        return "undefined";
      });

      return next === code ? null : { code: next, map: null };
    }
  };
}

function typescriptWithoutEsbuild() {
  return {
    name: "typescript-without-esbuild",
    enforce: "pre",
    transform(code, id) {
      const cleanId = id.split("?")[0];
      const isTypeScript = /\.(ts|tsx)$/.test(cleanId) || id.includes("lang.ts");
      if (!isTypeScript || cleanId.endsWith(".d.ts")) return null;

      const transpiled = ts.transpileModule(code, {
        fileName: cleanId,
        compilerOptions: {
          target: ts.ScriptTarget.ES2020,
          module: ts.ModuleKind.ESNext,
          jsx: ts.JsxEmit.Preserve,
          sourceMap: false
        }
      });

      return { code: transpiled.outputText, map: null };
    }
  };
}

export default defineConfig(({ command, mode }) => {
  const debugBuild = process.env.SCENIC_DEBUG_BUILD === "true" || mode === "debug";
  const minifyBuild = command === "build" && !debugBuild;

  return {
    plugins: [inlineEnvForRestrictedShell(command, mode), typescriptWithoutEsbuild(), vue()],
    cacheDir: "../.tmp/vite-cache",
    esbuild: false,
    keepProcessEnv: true,
    environments: {
      client: {
        keepProcessEnv: true
      }
    },
    resolve: {
      preserveSymlinks: true
    },
    optimizeDeps: {
      noDiscovery: true,
      include: []
    },
    server: {
      host: "127.0.0.1",
      port: 5173
    },
    build: {
      minify: minifyBuild ? "terser" : false,
      cssMinify: minifyBuild ? "lightningcss" : false,
      emptyOutDir: true,
      chunkSizeWarningLimit: 550,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes("node_modules/echarts") || id.includes("node_modules/zrender")) return "charts";
          }
        }
      }
    }
  };
});
