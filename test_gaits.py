import time, vcat
import os, tempfile
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()
st = vcat.load_state(); st["decor"] = []; st["messes"] = []; st["animals"] = []
app = vcat.VCat(st); app.update()
app.next_mouse = app.next_bird = time.monotonic() + 9999; app.chase_cd = 9999

def drive(sec, until=None):
    t0 = time.monotonic()
    while time.monotonic() - t0 < sec:
        app.update()
        if until and until():
            break
        time.sleep(0.005)

# --- gait_of mapping sanity ---
print("gait_of: frog=%s penguin=%s dragon=%s cat=%s bunny=%s" % (
    vcat.gait_of("frog"), vcat.gait_of("penguin"),
    vcat.gait_of("dragon"), vcat.gait_of("cat"), vcat.gait_of("bunny")))

# --- gait_render returns sane (dy, anim) for each gait while moving ---
for sp in ("frog", "penguin", "dragon", "cat"):
    dy, a2 = vcat.gait_render(sp, "walk", 0.3, 3.0, True)
    print("gait_render moving %-8s -> dy=%6.2f anim=%s" % (sp, dy, a2))
# not moving -> no bob (except flutter which always hovers)
for sp in ("frog", "dragon"):
    dy, a2 = vcat.gait_render(sp, "idle", 0.3, 3.0, False)
    print("gait_render idle   %-8s -> dy=%6.2f anim=%s" % (sp, dy, a2))

# --- every species draws in walk without crashing, _gait_dy gets set ---
app.clear_animals()
bad = []
for sp in vcat.SPECIES:
    app.clear_animals()
    an = app.spawn_animal(sp, x=app.x)
    an.birth = time.time() - 200            # adult
    an.set("walk", "walk", 8); an.target = app.x + 400
    try:
        for _ in range(40):
            an.tick(0.03)
        assert hasattr(an, "_gait_dy")
    except Exception as e:
        bad.append((sp, repr(e)))
print("walk-draw all species ok:", not bad, bad or "")

# --- force each new idle state on a flock; ensure they transition, no freeze ---
app.clear_animals()
flock = [app.spawn_animal("bunny", x=app.x + i * 30) for i in range(4)]
for a in flock:
    a.birth = time.time() - 200; a.hunger = 90
states_seen = set()
err = []
t0 = time.monotonic()
while time.monotonic() - t0 < 10:
    for a in flock:
        try:
            a.tick(0.03)
            states_seen.add(a.state)
        except Exception as e:
            err.append(repr(e)); break
    if err:
        break
    time.sleep(0.004)
print("flock states seen:", sorted(states_seen))
print("new states exercised:", sorted(states_seen & {"look", "groom", "stretch", "play", "lie", "sleep"}))
print("flock errors:", err or "none")

# --- explicitly drive look/groom/stretch/play to verify they time out to idle ---
app.clear_animals()
a = app.spawn_animal("cat", x=app.x); a.birth = time.time() - 200; a.hunger = 90
for state, anim in (("look", "blink"), ("groom", "groom"),
                    ("stretch", "stretch"), ("play", "tailchase")):
    a.set(state, anim, 1.0)
    out = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < 4:
        a.tick(0.03)
        if a.state != state:
            out = a.state; break
        time.sleep(0.004)
    print("state %-8s -> transitioned to %s" % (state, out))

app.quit_app(); print("ALL OK")
