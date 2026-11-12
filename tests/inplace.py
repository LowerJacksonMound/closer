"""In-place run and serve, from the outside: unittest over the real launcher (closer-mcp.sh) on stdio, plan approved by
a fake person, every file in the repo snapshotted before and after. Aimed at what the no-copy run could have broken.
python3 tests/inplace.py [-v]"""
import hashlib, json, os, shutil, subprocess, tempfile, threading, time, unittest
from pathlib import Path

CLOSER = Path(__file__).resolve().parent.parent
ST = {"purpose": "p", "intent": "i", "agrees": True}


class Server:
    def __init__(self, repo):
        self.p = subprocess.Popen([str(CLOSER / "closer-mcp.sh"), str(repo)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True)
        self.n = 0
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {"elicitation": {}}})
        t = self.call("cl_plan", {"intent": "a shop", "expectation": "it works"})
        assert t.startswith("APPROVED"), t

    def rpc(self, method, params):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}) + "\n"); self.p.stdin.flush()
        while True:
            m = json.loads(self.p.stdout.readline())
            if m.get("method") == "elicitation/create":  # the person says yes
                self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": {"action": "accept", "content": {}}}) + "\n"); self.p.stdin.flush()
            elif m.get("id") == self.n:
                return m["result"]

    def call(self, name, args):
        return self.rpc("tools/call", {"name": name, "arguments": args})["content"][0]["text"]

    def submit(self, file, source, checks):
        t = self.call("cl_submit", {"file": file, "source": source, "checks": checks, "stance": ST})
        return t.splitlines()[-1]

    def close(self):
        self.p.kill(); self.p.wait(); self.p.stdin.close(); self.p.stdout.close()


def snapshot(root):
    return {str(p.relative_to(root)): (p.stat().st_size, hashlib.md5(p.read_bytes()).hexdigest())
            for p in Path(root).rglob("*") if p.is_file()}


class InPlace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(); os.environ["CLOSER_HOME"] = cls.home
        cls.repo = Path(tempfile.mkdtemp()).resolve()
        w = lambda rel, text: ((cls.repo / rel).parent.mkdir(parents=True, exist_ok=True), (cls.repo / rel).write_text(text))
        w("shop/__init__.py", "from shop.cart import first\n")  # the package imports the target module itself
        w("shop/models.py", "class Item:\n    def __init__(self, name, price):\n        self.name, self.price = name, price\n")
        w("shop/cart.py", "def first():\n    return 1\n")
        w("shop/rates.json", json.dumps({"usd": 1.0, "eur": 0.9}))
        for i in range(3000):  # bulk the repo so a copy would show in the clock
            w(f"bulk/d{i % 30}/f{i}.py", f"X = {i}\n")
        w("bulk/blob.bin", "0" * 50_000_000)
        cls.srv = Server(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.srv.close(); shutil.rmtree(cls.repo); shutil.rmtree(cls.home)

    def setUp(self):
        self.before = snapshot(self.repo)

    def check_untouched(self, *written):
        after = snapshot(self.repo)
        self.assertEqual({k for k in set(self.before) | set(after) if self.before.get(k) != after.get(k)}, set(written))
        self.assertFalse([p for p in self.repo.rglob("__pycache__")], "pyc written into the real repo")
        self.assertFalse([p for p in self.repo.rglob("*closer*")], "temp file left in the real repo")

    def test_file_relative_data(self):  # a function that reads a sibling file through __file__
        src = "def rate(cur):\n    import json, pathlib\n    return json.loads(pathlib.Path(__file__).with_name('rates.json').read_text())[cur]\n"
        v = self.srv.submit("shop/cart.py", src, [{"call": "rate('eur')", "expect": 0.9}, {"call": "rate('x')", "raises": "KeyError"}])
        self.assertTrue(v.startswith("PASS"), v)
        self.check_untouched("shop/cart.py")

    def test_relative_import_in_source(self):
        src = "from .models import Item\n\ndef cheapest(names):\n    return min((Item(n, len(n)) for n in names), key=lambda i: i.price).name\n"
        v = self.srv.submit("shop/cart.py", src, [{"call": "cheapest(['aaa', 'b', 'cc'])", "expect": "b"}])
        self.assertTrue(v.startswith("PASS"), v)
        self.assertIn("from .models import Item", (self.repo / "shop/cart.py").read_text())
        self.check_untouched("shop/cart.py")

    def test_package_init_imports_target(self):  # shop/__init__ does `from shop.cart import first`; first must survive
        v = self.srv.submit("shop/cart.py", "def second():\n    return first() + 1\n", [{"call": "second()", "expect": 2}])
        self.assertTrue(v.startswith("PASS"), v)
        self.check_untouched("shop/cart.py")

    def test_new_file_in_new_package_dir(self):  # the dir exists nowhere but the temp tree until the write
        v = self.srv.submit("pricing/fx.py", "def dbl(x):\n    return x * 2\n", [{"call": "dbl(2)", "expect": 4}])
        self.assertTrue(v.startswith("PASS"), v)
        self.assertEqual((self.repo / "pricing/fx.py").read_text(), "def dbl(x):\n    return x * 2\n")
        self.check_untouched("pricing/fx.py")

    def test_serve_class_method_two_bodies(self):
        src = ("class Fx:\n    def __init__(self, base):\n        self.base = base\n"
               "    def rate(self, url):\n        import urllib.request\n        return self.base * float(urllib.request.urlopen(url, timeout=3).read())\n")
        checks = [{"call": ["Fx(2)", ".rate(url)"], "serve": {"body": "1.5"}, "expect": 3.0},
                  {"call": ["Fx(2)", ".rate(url)"], "serve": {"body": "0.25"}, "expect": 0.5}]
        v = self.srv.submit("pricing/fx.py", src, checks)
        self.assertTrue(v.startswith("PASS"), v)
        self.check_untouched("pricing/fx.py")

    def test_serve_with_given(self):
        src = ("def price_in(item, url):\n    import urllib.request\n"
               "    return round(item.price * float(urllib.request.urlopen(url, timeout=3).read()), 2)\n")
        checks = [{"call": "price_in(it, url)", "given": {"it": "shop.models.Item('a', 10.0)"}, "serve": {"body": "0.9"}, "expect": 9.0},
                  {"call": "price_in(it, url)", "given": {"it": "shop.models.Item('a', 10.0)"}, "serve": {"body": "1.1"}, "expect": 11.0}]
        v = self.srv.submit("shop/cart.py", src, checks)
        self.assertTrue(v.startswith("PASS"), v)
        self.check_untouched("shop/cart.py")

    def test_serve_status_via_http_client(self):
        src = ("def ping(url):\n    import http.client, urllib.parse\n    p = urllib.parse.urlparse(url)\n"
               "    c = http.client.HTTPConnection(p.hostname, p.port, timeout=3)\n    c.request('HEAD', '/')\n    return c.getresponse().status\n")
        v = self.srv.submit("shop/cart.py", src, [{"call": "ping(url)", "serve": {"body": "", "status": 503}, "expect": 503},
                                                   {"call": "ping(url)", "serve": {"body": ""}, "expect": 200}])
        self.assertTrue(v.startswith("PASS"), v)
        self.check_untouched("shop/cart.py")

    def test_serve_wrong_is_counterfeit_and_outside_net_is_fail(self):
        src = "def conv(url):\n    import urllib.request\n    return float(urllib.request.urlopen(url, timeout=3).read()) + 1\n"
        v = self.srv.submit("shop/cart.py", src, [{"call": "conv(url)", "serve": {"body": "1.5"}, "expect": 1.5}])
        self.assertTrue(v.startswith("FAIL try 1/2: counterfeit"), v)
        v = self.srv.submit("shop/cart.py", src, [{"call": "conv('http://example.com/')", "expect": 1.5}])
        self.assertTrue(v.startswith("HOLE") and "serve" in v, v)
        self.check_untouched()

    def test_speed_in_place(self):
        t = time.time()
        v = self.srv.submit("shop/cart.py", "def third():\n    return 3\n", [{"call": "third()", "expect": 3}])
        dt = time.time() - t
        self.assertTrue(v.startswith("PASS"), v)
        self.assertLess(dt, 1.5, f"{dt:.1f}s for one submission on a 3000-file, 50MB repo")
        self.check_untouched("shop/cart.py")

    def test_two_servers_at_once(self):  # two agents on one repo: the lock serialises, both land
        out = {}
        def go(k):
            s = Server(self.repo)
            out[k] = s.submit("shop/cart.py", f"def {k}(x):\n    return x + {len(k)}\n", [{"call": f"{k}(1)", "expect": 1 + len(k)}])
            s.close()
        ts = [threading.Thread(target=go, args=(k,)) for k in ("alpha", "beta")]
        [t.start() for t in ts]; [t.join(60) for t in ts]
        self.assertTrue(all(v.startswith("PASS") for v in out.values()), out)
        text = (self.repo / "shop/cart.py").read_text()
        self.assertIn("def alpha", text); self.assertIn("def beta", text)
        compile(text, "cart.py", "exec")
        self.check_untouched("shop/cart.py")


if __name__ == "__main__":
    import sys
    unittest.main(argv=[sys.argv[0]] + [a for a in sys.argv[1:] if a.startswith("-")])  # selftest.sh passes ". <tmpdir>"; not test names
