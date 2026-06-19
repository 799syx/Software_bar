import fs from "node:fs";
import path from "node:path";

const pluginPath = path.resolve("node_modules/@vitejs/plugin-vue/dist/index.mjs");
const marker = "restricted-shell-typescript-transpile";

if (!fs.existsSync(pluginPath)) {
  throw new Error(`Cannot find ${pluginPath}. Run npm install before starting the dev server or build.`);
}

let source = fs.readFileSync(pluginPath, "utf8");

if (!source.includes(marker)) {
  const importNeedle = "import { normalizePath as normalizePath$1, isCSSRequest, transformWithEsbuild, formatPostcssSourceMap, createFilter } from 'vite';\n";
  if (!source.includes(importNeedle)) {
    throw new Error("Unsupported @vitejs/plugin-vue build: Vite import line was not found.");
  }
  source = source.replace(importNeedle, `${importNeedle}import ts from 'typescript';\n`);

  const esbuildBlock = `      const { code: code2, map } = await transformWithEsbuild(
        resolvedCode,
        filename,
        {
          target: "esnext",
          charset: "utf8",
          // #430 support decorators in .vue file
          // target can be overridden by esbuild config target
          ...options.devServer?.config.esbuild,
          loader: "ts",
          sourcemap: options.sourceMap
        },
        resolvedMap
      );
      resolvedCode = code2;
      resolvedMap = resolvedMap ? map : resolvedMap;`;

  if (!source.includes(esbuildBlock)) {
    throw new Error("Unsupported @vitejs/plugin-vue build: SFC esbuild transform block was not found.");
  }

  const typescriptBlock = `      // ${marker}: this Windows sandbox blocks esbuild's service process.
      const transpiled = ts.transpileModule(resolvedCode, {
        fileName: filename,
        compilerOptions: {
          target: ts.ScriptTarget.ESNext,
          module: ts.ModuleKind.ESNext,
          sourceMap: Boolean(options.sourceMap),
          inlineSources: Boolean(options.sourceMap)
        }
      });
      resolvedCode = transpiled.outputText;
      resolvedMap = resolvedMap && transpiled.sourceMapText ? JSON.parse(transpiled.sourceMapText) : resolvedMap;`;

  source = source.replace(esbuildBlock, typescriptBlock);
  fs.writeFileSync(pluginPath, source, "utf8");
}

console.log("@vitejs/plugin-vue is ready for the restricted shell build.");
