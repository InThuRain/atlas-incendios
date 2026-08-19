#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const topojson = require('topojson-server');

if (process.argv.length < 4 || process.argv.length > 5) {
  console.error('Usage: convert_topojson.js INPUT.geojson OUTPUT.topojson [quantization]');
  process.exit(2);
}

const inputPath = process.argv[2];
const outputPath = process.argv[3];
const quantizationArgument = process.argv[4] || '1000000';
const quantization = quantizationArgument === 'none' ? null : Number(quantizationArgument);
if (quantization !== null && (!Number.isInteger(quantization) || quantization < 2)) {
  console.error('quantization must be an integer >= 2 or "none"');
  process.exit(2);
}

const source = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const topology = quantization === null
  ? topojson.topology({perimeters: source})
  : topojson.topology({perimeters: source}, quantization);
topology.metadata = {
  source_path: inputPath,
  source_feature_count: source.features.length,
  quantization: quantization,
  geometry_deduplicated: false
};
fs.mkdirSync(path.dirname(outputPath), {recursive: true});
fs.writeFileSync(outputPath, JSON.stringify(topology) + '\n');
console.log(JSON.stringify({
  input: inputPath,
  output: outputPath,
  feature_count: topology.objects.perimeters.geometries.length,
  bytes: fs.statSync(outputPath).size,
  quantization: quantization
}));
