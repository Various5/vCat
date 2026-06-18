import time, vcat
import os, tempfile
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()
st = vcat.load_state(); st["decor"] = []; st["messes"] = []; st["animals"] = []
app = vcat.VCat(st); app.update()

# --- bug frames are well-formed (12 wide, 8 rows, valid palette chars) ---
bad = []
for name in ("bug1", "bug2", "bugflat"):
    grid = vcat.CRITTER_FRAMES[name]
    w = len(grid[0])
    for i, r in enumerate(grid):
        if len(r) != w or any(ch not in vcat.PAL for ch in r):
            bad.append((name, i))
print("bug art well-formed:", not bad, bad or "")

# --- critters spawn in several types and run their full lifecycle ---
types_seen = set()
err = []
for _ in range(40):
    try:
        c = vcat.Critter(app)
        types_seen.add(c.type)
        for _ in range(20):
            c.tick(0.05)
        c.drop_at(app.x, app.ground())   # exercises the per-type "flat" frame
        c.rescale()
        c.despawn()
    except Exception as e:
        err.append(repr(e)); break
print("critter types seen:", sorted(types_seen), "| errors:", err or "none")

# --- birds spawn in several colours and fly/swoop without crashing ---
pals_seen = set()
err = []
for _ in range(40):
    try:
        b = vcat.Bird(app)
        pals_seen.add(None if b._pal is None else b._pal.get("B"))
        for _ in range(30):
            b.tick(0.05)
        b.rescale()
        b.despawn()
    except Exception as e:
        err.append(repr(e)); break
print("bird colours seen:", len(pals_seen), "of", len(vcat.BIRD_PALS), "| errors:", err or "none")

app.quit_app(); print("ALL OK")
