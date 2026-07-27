// Linter del motor de Shorts. Extrae el <script> de los HTML y lo pasa por ESLint.
//
//   node tools/lint_motor.mjs
//
// Por qué: `check_motor.mjs` caza errores de SINTAXIS (el archivo no arranca). Esto caza los que
// SÍ arrancan y fallan en silencio. En una sola sesión perdí tiempo con dos que la regla
// `no-redeclare` marca al instante:
//   · `pintarChecklist` ya existía para el panel de producción → la escena del canvas salía en
//     blanco, sin ningún error en consola.
//   · `reloj` ya estaba declarado dentro de `alinearPalabras` → el script entero abortaba.
// Solo reglas de CORRECCIÓN, ninguna de estilo: aquí no se discute cómo se escribe, se buscan
// bugs. Sale 0 si está limpio, 1 con la lista y su línea en el HTML real.

import { readFileSync } from 'node:fs';
import { ESLint } from 'eslint';

const ARCHIVOS = ['docs/guiones/short-renderer.html', 'docs/guiones/tests-motor.html'];

const eslint = new ESLint({
  overrideConfigFile: true,
  overrideConfig: {
    languageOptions: { ecmaVersion: 2024, sourceType: 'script' },
    linterOptions: { reportUnusedDisableDirectives: false },
    rules: {
      // declaraciones que se pisan entre sí — las dos que costaron tiempo hoy
      'no-redeclare': 'error',
      'no-func-assign': 'error',
      'no-dupe-keys': 'error',        // dos veces la misma clave en un objeto: gana la última
      'no-dupe-args': 'error',
      'no-dupe-else-if': 'error',
      // código que no puede ejecutarse o que no hace lo que parece
      'no-unreachable': 'error',
      'no-self-assign': 'error',
      'no-sparse-arrays': 'error',
      'no-cond-assign': ['error', 'always'],
      'no-constant-binary-expression': 'error',
      'no-unsafe-negation': 'error',
      'use-isnan': 'error',
      'valid-typeof': 'error',
    },
  },
});

let problemas = 0;

for (const archivo of ARCHIVOS) {
  const html = readFileSync(archivo, 'utf8');
  const bloques = [...html.matchAll(/<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/g)];
  for (const m of bloques) {
    const lineaBase = html.slice(0, m.index).split('\n').length;   // para dar la línea del HTML
    const [res] = await eslint.lintText(m[1], { filePath: 'motor.js' });
    for (const msg of res.messages) {
      problemas++;
      console.error(`${archivo}:${lineaBase + msg.line - 1}  ${msg.ruleId ?? 'parse'}  ${msg.message}`);
    }
  }
}

if (problemas) {
  console.error(`\n${problemas} problema(s) de corrección. Ninguno daría error en consola: ` +
                `el navegador ejecuta el archivo igual y falla en silencio.`);
  process.exit(1);
}
console.log('Motor limpio: sin redeclaraciones, claves duplicadas ni código muerto.');
