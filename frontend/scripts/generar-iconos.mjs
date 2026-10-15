// PNG reproducibles sin dependencias nativas; el diseño mantiene el área segura maskable.
import { writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';
import { fileURLToPath, URL } from 'node:url';
import { Buffer } from 'node:buffer';

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit++)
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(tipo, datos) {
  const nombre = Buffer.from(tipo);
  const largo = Buffer.alloc(4);
  largo.writeUInt32BE(datos.length);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([nombre, datos])));
  return Buffer.concat([largo, nombre, datos, crc]);
}
for (const size of [192, 512]) {
  const datos = Buffer.alloc((size * 4 + 1) * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const nx = (x / size - 0.5) * 2;
      const ny = (y / size - 0.5) * 2;
      const giroX = nx * 0.8 + ny * 0.6;
      const giroY = -nx * 0.6 + ny * 0.8;
      const hoja = (giroX * giroX) / 0.12 + (giroY * giroY) / 0.35 < 1;
      const tallo = Math.abs(nx + ny * 0.6) < 0.025 && ny > -0.15 && ny < 0.6;
      const color = hoja || tallo ? [238, 245, 213] : [22, 101, 52];
      const offset = y * (size * 4 + 1) + 1 + x * 4;
      datos.set([...color, 255], offset);
    }
  }
  const cabecera = Buffer.alloc(13);
  cabecera.writeUInt32BE(size, 0);
  cabecera.writeUInt32BE(size, 4);
  cabecera[8] = 8;
  cabecera[9] = 6;
  const png = Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', cabecera),
    chunk('IDAT', deflateSync(datos)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
  writeFileSync(
    fileURLToPath(new URL(`../public/brock-${size}.png`, import.meta.url)),
    png,
  );
}
