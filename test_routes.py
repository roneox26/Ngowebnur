# -*- coding: utf-8 -*-
from app import app

print("=" * 60)
print("All Routes List")
print("=" * 60)

routes = []
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        routes.append({
            'endpoint': rule.endpoint,
            'methods': ', '.join(rule.methods - {'HEAD', 'OPTIONS'}),
            'path': str(rule)
        })

routes.sort(key=lambda x: x['path'])

for route in routes:
    print(f"\n{route['path']}")
    print(f"  Endpoint: {route['endpoint']}")
    print(f"  Methods: {route['methods']}")

print("\n" + "=" * 60)
print(f"Total Routes: {len(routes)}")
print("=" * 60)
