#!/usr/bin/env node
'use strict';

const fs = require('fs');
const topojson = require('topojson-client');

if (process.argv.length < 4 || process.argv.length > 5) {
  console.error('Usage: parse_benchmark.js FORMAT FILE [repetitions]');
  process.exit(2);
}

const format = process.argv[2];
const filePath = process.argv[3];
const repetitions = Number(process.argv[4] || 7);
const source = fs.readFileSync(filePath, 'utf8');

function elapsedMilliseconds(start) {
  const elapsed = process.hrtime(start);
  return elapsed[0] * 1000 + elapsed[1] / 1000000;
}

function featureCount(parsed) {
  if (format === 'geojson') return parsed.features.length;
  if (format === 'compact_json') return parsed.features.length;
  if (format === 'topojson') return parsed.objects.perimeters.geometries.length;
  throw new Error('Unknown format: ' + format);
}

const parseTimes = [];
const decodeTimes = [];
const heapDeltas = [];
let count = null;
for (let index = 0; index < repetitions; index += 1) {
  if (global.gc) global.gc();
  const heapBefore = process.memoryUsage().heapUsed;
  const parseStart = process.hrtime();
  const parsed = JSON.parse(source);
  parseTimes.push(elapsedMilliseconds(parseStart));
  count = featureCount(parsed);
  if (format === 'topojson') {
    const decodeStart = process.hrtime();
    const decoded = topojson.feature(parsed, parsed.objects.perimeters);
    decodeTimes.push(elapsedMilliseconds(decodeStart));
    if (decoded.features.length !== count) throw new Error('TopoJSON decode lost features');
  }
  heapDeltas.push(Math.max(0, process.memoryUsage().heapUsed - heapBefore));
}

function summary(values) {
  const ordered = values.slice().sort((left, right) => left - right);
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  return {
    min: ordered[0],
    median: ordered[Math.floor(ordered.length / 2)],
    max: ordered[ordered.length - 1],
    mean: mean
  };
}

console.log(JSON.stringify({
  runtime: process.version,
  format: format,
  path: filePath,
  bytes: Buffer.byteLength(source),
  repetitions: repetitions,
  geometry_count: count,
  parse_ms: summary(parseTimes),
  decode_ms: decodeTimes.length ? summary(decodeTimes) : null,
  heap_delta_bytes: summary(heapDeltas)
}));
