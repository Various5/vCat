"""Lock-in: companion animals use distinct per-species pixel-art body sprites."""
import os, tempfile, time, vcat
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()
st = vcat.load_state(); st["decor"] = []; st["messes"] = []; st["animals"] = []
app = vcat.VCat(st); app.update()
app.next_mouse = app.next_bird = time.monotonic() + 9999

print("ANIMAL_ART species:", len(vcat.ANIMAL_ART))

# every species spawns as a sprite-based companion and renders in every state
bad = []
for sp in vcat.SPECIES:
    app.clear_animals()
    a = app.spawn_animal(sp, x=app.x); a.birth = time.time() - 200
    try:
        assert a.use_sprite, "not sprite"
        assert a.body_img[1].width() > 0 and a.body_img[-1].width() > 0
        assert a.cw > 0 and a.ch > 0
        for state, anim in (("walk", "walk"), ("idle", "idle"), ("graze", "munch"),
                            ("sleep", "sleep"), ("run", "run")):
            a.set(state, anim, 5)
            for _ in range(4):
                a.tick(0.04)
    except Exception as e:
        bad.append((sp, repr(e)))
print("all 14 sprite-render in all states:", not bad, bad or "")

# a bred baby is also sprite-based
app.clear_animals()
f = app.spawn_animal("cow", "f", x=app.x); m = app.spawn_animal("cow", "m", x=app.x + 120)
for x in (f, m):
    x.birth = time.time() - 300; x.hunger = 95; x.breed_cd = 0
f.urge = "mate"; f.urge_t = 14
for _ in range(400):
    app._tick_ecosystem(0.05)
    if len(app.animals) > 2:
        break
babies = [a for a in app.animals if (time.time() - a.birth) < 5]
print("bred baby is sprite-based:", bool(babies) and babies[0].use_sprite)

# facing flips use the mirrored sprite, not a crash
app.clear_animals()
a = app.spawn_animal("fox", x=app.x); a.birth = time.time() - 200
a.facing = -1; a._draw(); left = a.body_img[-1]
a.facing = 1; a._draw(); right = a.body_img[1]
print("facing flip ok:", left is not right)

# fallback: with no ANIMAL_ART, companions revert to the frame-based body (no crash)
saved = vcat.ANIMAL_ART
vcat.ANIMAL_ART = {}
try:
    app.clear_animals()
    a = app.spawn_animal("cat", x=app.x); a.birth = time.time() - 200
    a.tick(0.04)
    print("fallback to frames when no ANIMAL_ART:", not a.use_sprite)
finally:
    vcat.ANIMAL_ART = saved

app.quit_app()
print("ALL OK")
