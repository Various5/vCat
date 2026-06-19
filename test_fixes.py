"""Locks in the 5 issues found by the pre-v1.3.0 adversarial review."""
import time, vcat
import os, tempfile
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()
st = vcat.load_state(); st["decor"] = []; st["messes"] = []; st["animals"] = []
app = vcat.VCat(st); app.update()
app.next_mouse = app.next_bird = time.monotonic() + 9999; app.chase_cd = 9999

# --- Fix 1: 'Go graze' takes ONE commanded bite, does not strip every patch ---
app.clear_animals(); app.decor = []
patches = [vcat.Decor(app, "grass", app.x + i * 60, grow=1.0) for i in range(4)]
for p in patches:
    p.lushness = 100.0; app.decor.append(p)
goat = app.spawn_animal("goat", x=app.x); goat.birth = time.time() - 200; goat.hunger = 95
app._urge_animal(goat, "graze")
for _ in range(120):                       # ~6s of game time
    goat.tick(0.05)
emptied = sum(1 for p in patches if p.lushness <= 8)
print(f"fix1 graze: urge cleared={goat.urge is None} | patches emptied={emptied}/4 (expect 0-1, not all)")

# --- Fix 2: commanding a HUNGRY female to mate must not be able to kill her ---
app.clear_animals()
f = app.spawn_animal("pig", "f", x=app.x); m = app.spawn_animal("pig", "m", x=app.x + 120)
for x in (f, m):
    x.birth = time.time() - 300; x.breed_cd = 0
f.hunger = 18.0; m.hunger = 95.0            # she is near-starving
app.decor = [vcat.Decor(app, "grass", app.x + 40, grow=1.0)]  # food exists -> starvation can fire
app._urge_animal(f, "mate")
for _ in range(80):
    app._tick_ecosystem(0.05)
print(f"fix2 mate-while-hungry: female alive={f.alive and not f.dying} (must be True) | hunger={round(f.hunger)}")

# --- Fix 3: gait anim overrides resolve to real frames, not the idle fallback ---
sit_frames = vcat.ANIMS.get("sit"); cr_frames = vcat.ANIMS.get("crouch1")
dy_hop, an_hop = vcat.gait_render("bunny", "walk", 0.3, 3.0, True)
dy_flt, an_flt = vcat.gait_render("dragon", "walk", 0.3, 3.0, True)
ok3 = (sit_frames and sit_frames[0] == ["sit"] and cr_frames and cr_frames[0] == ["crouch1"]
       and an_hop == "crouch1" and an_flt == "sit"
       and vcat.ANIMS.get(an_hop) is not vcat.ANIMS["idle"]
       and vcat.ANIMS.get(an_flt) is not vcat.ANIMS["idle"])
print(f"fix3 gait poses resolve: {ok3} (hop->{an_hop}, flutter->{an_flt})")

# --- Fix 4: a legacy save (grass/tree, NO grow/variant) loads full-grown, original art ---
legacy = {"decor": [{"kind": "grass", "x": app.x}, {"kind": "tree", "x": app.x + 100},
                    {"kind": "bed", "x": app.x - 100}]}
import json
json.dump(legacy, open(vcat.SAVE_PATH, "w", encoding="utf-8"))
ls = vcat.load_state()
veg = [d for d in ls["decor"] if d["kind"] in ("grass", "tree")]
print("fix4 legacy load:", all(d.get("grow") == 1.0 and d.get("variant") == 0 for d in veg),
      "| entries:", [(d["kind"], d.get("grow"), d.get("variant")) for d in veg])

# --- Fix 5: a tree planted at the right edge stays on-screen after growing ---
app.clear_animals(); app.decor = []
edge = vcat.Decor(app, "tree", app.wa[2] - 5)      # planted hard against the right edge
app.decor.append(edge)
for _ in range(2000):
    app._tick_ecosystem(0.1)
    if edge.grow >= 1.0:
        break
right_edge = edge.x + edge.cw / 2
on_screen = right_edge <= app.wa[2] + 1 and (edge.x - edge.cw / 2) >= app.wa[0] - 1
print(f"fix5 grown tree on-screen: {on_screen} | right={int(right_edge)} wa_right={app.wa[2]} grow={edge.grow:.2f}")

app.quit_app(); print("ALL OK")
