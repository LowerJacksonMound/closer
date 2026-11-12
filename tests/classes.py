"""Class submissions: counterfeits must not be written, real ones must. python3 classes.py CLOSER_DIR"""
import os, shutil, sys, tempfile
sys.path.insert(0, sys.argv[1]); import judge
ST = {"purpose": "p", "intent": "i", "agrees": True}
SEED = {"shop/cartx.py": "","shop/__init__.py": "", "shop/models.py": "from dataclasses import dataclass\n\n@dataclass\nclass Item:\n    name: str\n    price: float\n    qty: int = 1\n",
        "shop/cart.py": "from shop.models import Item\n\n\nclass Cart:\n    def __init__(self):\n        self.items = []\n\n    def add(self, item):\n        self.items.append(item)\n\n    def total(self, rate):\n        return round(sum(i.price * i.qty for i in self.items) * (1 + rate), 2)\n"}
CART = "class Cart:\n    def __init__(self):\n        self.items = []\n\n    def add(self, item):\n        self.items.append(item)\n\n    def total(self, rate):\n        return round(sum(i.price * i.qty for i in self.items) * (1 + rate), 2)\n"
BAD = [
 ("given patches the fn", "def total(c):\n    return 0\n", [{"given": {"x": ["shop.models.Item('a', 1.0)", ".__init__('b', 2.0)"]}, "call": "total(x)", "expect": 1}]),
 ("given calls os", "def total(c):\n    return 0\n", [{"given": {"x": "os.system('true')"}, "call": "total(x)", "expect": 1}]),
 ("given non-repo class", "def total(c):\n    return 0\n", [{"given": {"x": "dict(a=1)"}, "call": "total(x)", "expect": 1}]),
 ("star import", "from os import *\ndef f():\n    return 1\n", [{"call": "f()", "expect": 1}]),
 ("code between", "import os\nos.system('x')\ndef f():\n    return 1\n", [{"call": "f()", "expect": 1}]),
 ("untested method", CART.replace("    def total", "    def hidden(self):\n        return 0\n\n    def total"),
  [{"call": ["Cart()", ".add(Item('a', 2.0))", ".total(0.5)"], "expect": 3.0}]),
 ("class body runs code", "class Cart:\n    x = print('hi')\n    def total(self):\n        return 1\n", [{"call": ["Cart()", ".total()"], "expect": 1}]),
 ("base-less class stepped through an unknown name", "class Cart:\n    def total(self):\n        return 0\n", [{"call": ["Cart()", ".args"], "expect": []}]),
 ("empty class", "class Cart:\n    pass\n", [{"call": "Cart()", "expect": {"__class__": "Cart"}}]),
 ("metaclass", "class Cart(metaclass=type):\n    def total(self):\n        return 1\n", [{"call": ["Cart()", ".total()"], "expect": 1}]),
 ("odd decorator", "@(lambda c: c)\nclass Cart:\n    def total(self):\n        return 1\n", [{"call": ["Cart()", ".total()"], "expect": 1}]),
 ("method rebinds later", None, None),
 ("step calls non-method", CART, [{"call": ["Cart()", ".__class__()"], "expect": 1}]),
 ("arg error posing as raises", "def f(x):\n    return 1\n", [{"call": "f(Item())", "raises": "TypeError"}]),
 ("total wrong", CART.replace("(1 + rate)", "1"), [{"call": ["Cart()", ".add(Item('a', 2.0))", ".total(0.5)"], "expect": 3.0}]),
 ("object faking eq", "def mk(n):\n    class Item:\n        def __eq__(s, o): return True\n    return Item()\n", [{"call": "mk('a')", "expect": {"__class__": "Item", "name": "a", "price": 2.0, "qty": 1}}]),
]
GOOD = [
 ("Cart full", CART, [{"call": ["Cart()", ".add(Item('a', 2.0, 2))", ".total(0.1)"], "expect": 4.4}, {"call": ["Cart()", ".add(Item('a', 1.0))"], "expect": None}]),
 ("returns Item", "def make_item(name, price, qty=1):\n    if price < 0:\n        raise ValueError('negative')\n    return Item(name, price, qty)\n",
  [{"call": "make_item('a', 2.5)", "expect": {"__class__": "Item", "name": "a", "price": 2.5, "qty": 1}}, {"call": "make_item('a', -1)", "raises": "ValueError"}]),
 ("dataclass + property", "from dataclasses import dataclass\n\n\n@dataclass\nclass Line:\n    price: float\n    qty: int = 1\n\n    @property\n    def cost(self):\n        return self.price * self.qty\n",
  [{"call": ["Line(2.0, 3)", ".cost"], "expect": 6.0}]),
 ("record dataclass, no methods", "from dataclasses import dataclass\n\n\n@dataclass\nclass Player:\n    name: str\n    score: int = 0\n",
  [{"call": "Player('a', 3)", "expect": {"__class__": "Player", "name": "a", "score": 3}}], "shop/models.py"),
 ("exception subclass stepped through an inherited attribute", "class LotError(ValueError):\n    pass\n",
  [{"call": ["LotError('row 2: year')", ".args"], "expect": ["row 2: year"]}]),
 ("module-path class", "def first(items):\n    return items[0].name\n", [{"call": "first([shop.models.Item('z', 1.0)])", "expect": "z"}]),
 ("new file w/ imports", "from shop.models import Item\nimport math\n\ndef mk(n):\n    return Item(n, math.floor(2.7))\n", [{"call": "mk('q')", "expect": {"__class__": "Item", "name": "q", "price": 2, "qty": 1}}], "shop/new.py"),
 ("given cart + classmethod", "from dataclasses import dataclass\n\n@dataclass\nclass Receipt:\n    total: float\n\n    @classmethod\n    def from_cart(cls, cart, rate):\n        return cls(cart.total(rate))\n",
  [{"given": {"cart": ["Cart()", ".add(shop.models.Item('a', 2.0, 2))"]}, "call": "Receipt.from_cart(cart, 0.5)", "expect": {"__class__": "Receipt", "total": 6.0}}], "shop/cart.py"),
 ("replace existing fn", "def cart_total(items):\n    return 1\n", [{"call": "cart_total([])", "expect": 1}]),
]
def go(label, src, checks, rel="shop/cart.py"):
    repo = tempfile.mkdtemp(); os.environ["CLOSER_HOME"] = tempfile.mkdtemp()
    for f, t in SEED.items():
        os.makedirs(os.path.dirname(os.path.join(repo, f)), exist_ok=True); open(os.path.join(repo, f), "w").write(t)
    if src is None:
        open(os.path.join(repo, rel), "a").write("\nclass Cart:\n    def total(self):\n        return 0\n\nCart.total = lambda self: 1\n")
        src, checks = "class Cart:\n    def total(self):\n        return 0\n", [{"call": ["Cart()", ".total()"], "expect": 1}]
    v, msg = judge.submit(repo, rel, src, checks, ST, "plan")
    if os.environ.get('SHOW') and v == 'PASS': print(open(os.path.join(repo, rel)).read())
    shutil.rmtree(repo); return v, msg.split("\n", 3)[-1][:150]
bad = 0
for l, s, c in BAD:
    v, m = go(l, s, c); bad += v == "PASS"; print(("WRITTEN " if v == "PASS" else "stopped ") + l + ": " + m)
for l, s, c, *r in GOOD:
    v, m = go(l, s, c, *r); print(("ok      " if v == "PASS" else "BROKEN  ") + l + ": " + m)
print(bad, "counterfeit class(es) written")
