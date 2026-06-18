import time, vcat
import os, tempfile
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()
st = vcat.load_state(); st["decor"] = []; st["messes"] = []; st["animals"] = []
app = vcat.VCat(st); app.update()
app.next_mouse = app.next_bird = time.monotonic() + 9999; app.chase_cd = 9999

# --- all veg kinds build without ragged/bad art, across all variants ---
bad = []
for kind, variants in vcat.VEG_VARIANTS.items():
    for vi in range(len(variants)):
        try:
            d = vcat.Decor(app, kind, app.x, variant=vi, grow=0.1)
            assert d.variant == vi
            assert d.cw > 0 and d.ch > 0
            d.destroy()
        except Exception as e:
            bad.append((kind, vi, repr(e)))
print("all veg variants render:", not bad, bad or "")

# --- variety: placing the same kind many times yields >1 distinct variant ---
app.decor = []
seen = set()
for _ in range(20):
    d = vcat.Decor(app, "grass", app.x)
    seen.add(d.variant); d.destroy()
print("grass variety: distinct variants seen =", sorted(seen), "(pool", len(vcat.VEG_VARIANTS["grass"]), ")")

# --- growth: a freshly planted tree starts small and grows taller ---
app.decor = []
tree = vcat.Decor(app, "tree", app.x); app.decor.append(tree)
ch0, g0 = tree.ch, tree.grow
for _ in range(2000):                       # simulate ~ a few min of game time
    app._tick_ecosystem(0.1)
    if tree.grow >= 1.0:
        break
print(f"tree growth: grow {g0:.2f} -> {tree.grow:.2f} | height {ch0}px -> {tree.ch}px (taller: {tree.ch > ch0})")

# --- edibility gate: a sprout isn't grazeable; a grown patch is ---
app.decor = []
sprout = vcat.Decor(app, "grass", app.x, grow=0.1); sprout.lushness = 100.0
grown = vcat.Decor(app, "grass", app.x, grow=1.0); grown.lushness = 100.0
print("edible gate: sprout edible =", sprout.edible(), "| grown edible =", grown.edible())
sprout.destroy(); grown.destroy()

# --- a bush is browsable food for herbivores; flowers grow too ---
app.decor = []
bush = vcat.Decor(app, "bush", app.x, grow=1.0); bush.lushness = 100.0
app.decor.append(bush)
goat = app.spawn_animal("goat", x=app.x + 8); goat.birth = time.time() - 200; goat.hunger = 20
h0 = goat.hunger
for _ in range(200):
    app._tick_ecosystem(0.05)
    if goat.hunger > h0 + 15:
        break
print("bush browse: goat hunger", round(h0), "->", round(goat.hunger), "| bush edible:", bush.edible())

# --- persistence round-trip keeps variant + growth ---
app.clear_animals(); app.decor = []
t = vcat.Decor(app, "flower", app.x, variant=2, grow=0.4); app.decor.append(t)
app._stash_save()
st2 = vcat.load_state()
d2 = st2["decor"][0]
print("save round-trip: kind", d2["kind"], "variant", d2.get("variant"), "grow", d2.get("grow"))

app.quit_app(); print("ALL OK")
