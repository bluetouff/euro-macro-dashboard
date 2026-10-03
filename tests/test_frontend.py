import json
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path


class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inline = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.inline = "src" not in dict(attrs)

    def handle_endtag(self, tag):
        if tag == "script":
            self.inline = False

    def handle_data(self, value):
        if self.inline:
            self.scripts.append(value)


@unittest.skipUnless(shutil.which("node"), "Node requis pour exécuter le JavaScript du site")
class FrontendFreshnessTest(unittest.TestCase):
    def render(self, hours=0, generated=None, view="", quality="ok", advance=0):
        parser = InlineScripts()
        parser.feed((Path(__file__).resolve().parents[1] / "index.html").read_text())
        harness = r"""
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const generated = '2026-10-02T05:32:01Z';
let now = Date.parse(generated) + input.hours * 3600000;
const nodes = {};
const callbacks = [];
const document = {getElementById(id){
  return nodes[id] ||= {innerHTML:'', textContent:'', hidden:false,
    classList:{toggle(name, value){this[name] = value;}}};
}};
const snapshot = {
  generated_at:input.generated ?? generated, quality:{status:input.quality},
  counts:{total:32, ok:32, warn:0, dang:0}, global_score:45,
  regime:{label:'Neutre'}, families:[], alerts:[], history:[], source_sha:'a'.repeat(40)
};
vm.runInNewContext(input.script, {
  window:{SNAPSHOT:snapshot, location:{search:input.view}}, document, URLSearchParams,
  Date:{now:()=>now, parse:Date.parse}, setInterval:(fn)=>callbacks.push(fn)
});
now += input.advance * 3600000;
callbacks.forEach(fn=>fn());
process.stdout.write(JSON.stringify({
  message:nodes['snapshot-freshness'].textContent,
  hidden:nodes['snapshot-freshness'].hidden,
  warning:nodes['snapshot-status'].classList['needs-attention'],
  html:nodes.app.innerHTML
}));
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", harness],
            input=json.dumps({"script": "\n".join(parser.scripts), "hours": hours,
                              "generated": generated, "view": view, "quality": quality,
                              "advance": advance}),
            text=True, capture_output=True, check=True, timeout=10,
        )
        return json.loads(result.stdout)

    def test_fresh_and_degraded_collection_status(self):
        self.assertFalse(self.render(hours=26)["warning"])
        self.assertTrue(self.render(hours=1)["hidden"])
        self.assertTrue(self.render(hours=1, quality="degraded")["warning"])

    def test_late_and_stale_both_views(self):
        for view in ("", "?view=faq"):
            with self.subTest(view=view):
                self.assertIn("en retard", self.render(hours=27, view=view)["message"])
                self.assertIn("en retard", self.render(hours=36, view=view)["message"])
                self.assertIn("périmé", self.render(hours=37, view=view)["message"])

    def test_invalid_future_and_aging_open_page(self):
        self.assertIn("non vérifiable", self.render(generated="invalid")["message"])
        self.assertIn("non vérifiable", self.render(hours=-1)["message"])
        self.assertIn("périmé", self.render(hours=1, advance=36)["message"])


if __name__ == "__main__":
    unittest.main()
