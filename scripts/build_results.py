"""Refresh the embedded results JSON without rerunning inference."""
from pathlib import Path
import json, re
root = Path(__file__).resolve().parents[1]
rows = json.loads((root/'data/sample_results.json').read_text(encoding='utf-8'))
payload = json.dumps(rows, ensure_ascii=False).replace('<', r'\u003c').replace('>', r'\u003e').replace('&', r'\u0026')
page = root/'results.html'
source = page.read_text(encoding='utf-8')
pattern = r'(<script id="data" type="application/json">).*?(</script>)'
updated, count = re.subn(pattern, lambda m: m[1]+payload+m[2], source, flags=re.S)
if count != 1: raise RuntimeError('Expected exactly one results data block')
page.write_text(updated, encoding='utf-8')
print(f'Updated {len(rows)} result rows. Review fixed report text separately.')
