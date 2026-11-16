// Convert the official Voron 0.2r1 STEP assembly into a web 3D file (GLB) for the virtual printer page.
//
//   node tools/cad/convert_step.mjs <input.step|.stp|.zip> src/assistant_v2/static/cad/voron02r1.glb
//
// Needs: npm i occt-import-js @gltf-transform/core @gltf-transform/functions meshoptimizer jszip
// What it does
//  1. reads the STEP file with OpenCascade (occt-import-js, WebAssembly), keeping the assembly tree names
//  2. writes one glTF node per solid; the node name = "Assembly/Sub-assembly/Part", so the page can map it to a part id
//  3. welds and simplifies the meshes (screws and fillets have huge triangle counts) to keep the file small
//  4. writes a list of all part names next to the GLB (names.json) for the mapping in cad_map.json
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const occtimportjs = require('occt-import-js');
const { Document, NodeIO } = require('@gltf-transform/core');
const { weld, simplify, dedup, prune } = require('@gltf-transform/functions');
const { MeshoptSimplifier } = require('meshoptimizer');

const [, , input, output] = process.argv;
if (!input || !output) { console.error('usage: node convert_step.mjs <input.step|zip> <output.glb>'); process.exit(1); }

let bytes = fs.readFileSync(input);
if (input.toLowerCase().endsWith('.zip')) {
  const JSZip = require('jszip'); const zip = await JSZip.loadAsync(bytes);
  const entry = Object.values(zip.files).find(f => /\.(step|stp)$/i.test(f.name));
  if (!entry) throw new Error('no .step file inside the zip');
  console.log('reading', entry.name); bytes = await entry.async('nodebuffer');
}
console.log(`STEP size ${(bytes.length / 1e6).toFixed(1)} MB, triangulating (this can take a few minutes) ...`);
const occt = await occtimportjs();
const res = occt.ReadStepFile(new Uint8Array(bytes), { linearUnit: 'millimeter', linearDeflectionType: 'bounding_box_ratio', linearDeflection: 0.002, angularDeflection: 0.6 });
if (!res.success) throw new Error('OpenCascade could not read the STEP file');
console.log(`meshes: ${res.meshes.length}`);

const doc = new Document(); const buf = doc.createBuffer(); const scene = doc.createScene('voron02r1');
const mats = new Map(); const names = [];
function material(color) {
  const key = (color || [0.6, 0.6, 0.6]).map(c => c.toFixed(2)).join(',');
  if (!mats.has(key)) mats.set(key, doc.createMaterial(key).setBaseColorFactor([...(color || [0.6, 0.6, 0.6]), 1]).setMetallicFactor(0.2).setRoughnessFactor(0.6));
  return mats.get(key);
}
function meshNode(i, label) {
  const m = res.meshes[i];
  const pos = doc.createAccessor().setType('VEC3').setArray(new Float32Array(m.attributes.position.array)).setBuffer(buf);
  const prim = doc.createPrimitive().setAttribute('POSITION', pos).setMaterial(material(m.color));
  if (m.attributes.normal) prim.setAttribute('NORMAL', doc.createAccessor().setType('VEC3').setArray(new Float32Array(m.attributes.normal.array)).setBuffer(buf));
  prim.setIndices(doc.createAccessor().setType('SCALAR').setArray(new Uint32Array(m.index.array)).setBuffer(buf));
  const name = `${label}/${m.name || 'solid' + i}`; names.push(name);
  return doc.createNode(name).setMesh(doc.createMesh(name).addPrimitive(prim));
}
function walk(node, parent, trail) {
  const label = [...trail, node.name || 'group'].filter(Boolean).join('/');
  const g = doc.createNode(label); parent.addChild(g);
  for (const i of node.meshes || []) g.addChild(meshNode(i, label));
  for (const c of node.children || []) walk(c, g, [...trail, node.name]);
}
const root = doc.createNode('root'); scene.addChild(root);
if (res.root) walk(res.root, root, []); else res.meshes.forEach((_, i) => root.addChild(meshNode(i, 'part')));

await MeshoptSimplifier.ready;
await doc.transform(dedup(), weld({ tolerance: 0.0001 }), simplify({ simplifier: MeshoptSimplifier, ratio: 0.35, error: 0.0015 }), prune());
fs.mkdirSync(path.dirname(output), { recursive: true });
await new NodeIO().write(output, doc);
fs.writeFileSync(path.join(path.dirname(output), 'names.json'), JSON.stringify(names, null, 1));
console.log(`written ${output} (${(fs.statSync(output).size / 1e6).toFixed(1)} MB), ${names.length} solids; names in names.json`);
