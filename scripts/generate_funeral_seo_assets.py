#!/usr/bin/env python3
# Generated SEO assets source: data/funeral-seo-facilities.json
# Index gate: current operation + official price + unique content + semantic fit.
import json, pathlib
R=pathlib.Path(__file__).resolve().parents[1]
s=json.loads((R/'data/funeral-seo-facilities.json').read_text(encoding='utf-8'))
print(len(s['facilities'])*len(s['visitor_bands'])*len(s['products']))
