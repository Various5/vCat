"""Lock-in for the health system: food/water/energy/comfort/love + overall health,
sickness (recovers with care), per-species comfort decor, for pet and flock."""
import os, tempfile, time, vcat
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()


def fresh(sp="cat", **kw):
    st = vcat.load_state()
    st.update(species=sp, created_ts=time.time() - 300000, decor=[], messes=[],
              animals=[], name="", **kw)
    a = vcat.VCat(st)
    a.update()
    a.next_mouse = a.next_bird = time.monotonic() + 9999
    return a


# main pet has the full stat set
app = fresh()
have = all(k in app.needs for k in ("hunger", "thirst", "love", "energy", "comfort"))
have = have and hasattr(app, "health") and hasattr(app, "sick")
print("main pet full stat set:", have)

# neglect -> sick; then care -> recovers (hysteresis)
for k in app.needs:
    app.needs[k] = 3.0
t = 0
while not app.sick and t < 8000:
    app.update_needs(0.3); t += 1
got_sick = app.sick
for k in app.needs:
    app.needs[k] = 95.0
t = 0
while app.sick and t < 8000:
    app.update_needs(0.3); t += 1
recovered = not app.sick
print("sickness: got sick =", got_sick, "| recovered with care =", recovered, "| health", round(app.health))

# per-species comfort: a cat near its box, a frog near a pond
app.quit_app()
for sp, kind in (("cat", "box"), ("frog", "pond"), ("cow", "grass")):
    a = fresh(sp)
    a.decor = [vcat.Decor(a, kind, a.x, grow=1.0)]
    a.needs["comfort"] = 30.0
    for _ in range(900):
        a.update_needs(0.3)
    print(f"  {sp} near {kind}: comfort 30 -> {round(a.needs['comfort'])}")
    a.quit_app()

# is_sad reflects sickness; begging ignores energy/comfort
app = fresh()
app.health = 10.0; app.sick = True
sad_when_sick = app.is_sad()
app.sick = False
for k in app.needs:
    app.needs[k] = 90.0
app.needs["energy"] = 1.0       # tired but not a "beg" need
begs = app.need_low()
print("is_sad when sick:", sad_when_sick, "| need_low ignores energy:", begs is None)
app.quit_app()

# companion flock has health too
app = fresh()
g = app.spawn_animal("goat", x=app.x); g.birth = time.time() - 200
comp = all(hasattr(g, a) for a in ("energy", "comfort", "health", "sick"))
g.hunger = 0.0
t = 0
while not g.sick and t < 8000:
    g._update_health(0.3); t += 1
print("companion has stats:", comp, "| companion can get sick:", g.sick)
app.quit_app()

# persistence round-trip
app = fresh()
app.needs["energy"] = 41.0; app.needs["comfort"] = 52.0; app.health = 63.0
app._stash_save()
st = vcat.load_state()
print("persist:", st.get("energy") == 41.0 and st.get("comfort") == 52.0 and st.get("health") == 63.0)
app.quit_app()
print("ALL OK")
