// Comprobación de SINTAXIS del motor de Shorts, sin abrir el navegador.
//
// Por qué existe: `short-renderer.html` es un solo archivo con ~5.000 líneas de JS en un <script>.
// Un error de sintaxis NO da error en consola — el navegador aborta el script entero y todas las
// funciones globales quedan sin definir, así que la página "carga" pero no hace nada. Ha pasado
// dos veces por la misma causa: un nombre YA DECLARADO en otro punto del archivo
// (`pintarChecklist`, `reloj`). Node lo caza en 200 ms.
//
//   node tools/check_motor.mjs
//
// Sale 0 si todo está bien; 1 con el error y su línea si no.

import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ARCHIVOS = ['docs/guiones/short-renderer.html', 'docs/guiones/tests-motor.html'];
let fallos = 0;

for (const archivo of ARCHIVOS) {
  const html = readFileSync(archivo, 'utf8');
  // todos los bloques <script> sin src
  const bloques = [...html.matchAll(/<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/g)];
  if (!bloques.length) { console.log(`· ${archivo}: sin <script> inline`); continue; }

  bloques.forEach((m, i) => {
    // línea donde empieza el bloque, para que el número de error sea el del HTML real
    const antes = html.slice(0, m.index).split('\n').length;
    const tmp = join(tmpdir(), `motor-check-${i}-${Date.now()}.js`);
    writeFileSync(tmp, m[1]);
    try {
      execFileSync(process.execPath, ['--check', tmp], { stdio: 'pipe' });
      console.log(`✓ ${archivo} (bloque ${i + 1}): sintaxis OK`);
    } catch (e) {
      fallos++;
      const salida = (e.stderr?.toString() || e.message).split('\n').slice(0, 6).join('\n');
      const linea = /:(\d+)\s*$/m.exec(salida.split('\n')[0] || '');
      console.error(`✗ ${archivo} (bloque ${i + 1}) — el <script> empieza en la línea ${antes} del HTML`);
      if (linea) console.error(`  → línea ${antes + (+linea[1]) - 1} del archivo`);
      console.error(salida.replace(/^/gm, '  '));
    } finally {
      try { unlinkSync(tmp); } catch {}
    }
  });
}

if (fallos) {
  console.error(`\n${fallos} bloque(s) con error de sintaxis. El navegador NO lo avisaría: ` +
                `abortaría el script y las funciones globales quedarían sin definir.`);
  process.exit(1);
}
console.log('\nSintaxis correcta en todos los bloques.');
