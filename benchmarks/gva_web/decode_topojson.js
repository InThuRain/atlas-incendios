#!/usr/bin/env node
'use strict';

const fs = require('fs');
const topojson = require('topojson-client');

if (process.argv.length !== 4) {
  console.error('Usage: decode_topojson.js INPUT.topojson OUTPUT.geojson');
  process.exit(2);
}

const source = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const decoded = topojson.feature(source, source.objects.perimeters);
fs.writeFileSync(process.argv[3], JSON.stringify(decoded) + '\n');
console.log(JSON.stringify({feature_count: decoded.features.length}));
