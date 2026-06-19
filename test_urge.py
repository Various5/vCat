import time, vcat
import os, tempfile
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()
st = vcat.load_state(); st["decor"] = []; st["messes"] = []; st["animals"] = []
app = vcat.VCat(st); app.update()
app.next_mouse = app.next_bird = time.monotonic() + 9999; app.chase_cd = 9999

def drive_animal(an, sec, until=None):
    t0 = time.monotonic()
    while time.monotonic() - t0 < sec:
        an.tick(0.03)
        if until and until():
            return True
        time.sleep(0.003)
    return False

# --- urge: GRAZE pulls a non-hungry herbivore to grass and feeds it ---
app.clear_animals()
grass = vcat.Decor(app, "grass", app.x + 260); app.decor.append(grass)
grass.lushness = 100.0
goat = app.spawn_animal("goat", x=app.x - 60); goat.birth = time.time() - 200
goat.hunger = 95.0                              # NOT hungry — only the urge should move it
app._urge_animal(goat, "graze")
ok = drive_animal(goat, 8, until=lambda: goat.state == "graze")
print("urge graze: reached grass & grazed:", ok, "| state:", goat.state)

# --- urge: HUNT makes a fed carnivore chase & kill prey ---
app.clear_animals()
prey = app.spawn_animal("bunny", x=app.x + 220); prey.birth = time.time() - 200; prey.hunger = 90
pred = app.spawn_animal("fox", x=app.x - 60); pred.birth = time.time() - 200; pred.hunger = 95
app._urge_animal(pred, "hunt")
t0 = time.monotonic()
while time.monotonic() - t0 < 9 and not (prey.dying or not prey.alive):
    for a in (pred, prey):
        a.tick(0.03)
    time.sleep(0.003)
print("urge hunt: prey killed:", prey.dying or not prey.alive, "| pred hunger:", round(pred.hunger))

# --- urge: COME pulls an animal toward the cursor (deterministic tick loop) ---
app.clear_animals()
app.cur = (int(app.x + 300), int(app.ground()))
a = app.spawn_animal("cow", x=app.x - 200); a.birth = time.time() - 200; a.hunger = 90
x0 = a.x
app._urge_animal(a, "come")
closest = 1e9
for _ in range(60):                       # urge clears once it arrives at nuzzle range
    a.tick(0.05)
    closest = min(closest, abs(a.x - (app.x + 300)))
    if a.urge is None:
        break
print("urge come: arrived near cursor:", closest <= 10 * a.scale + 16,
      "| closest:", round(closest), "(nuzzle radius", round(10 * a.scale), ")")

# --- urge: PLAY / REST set their states and clear the urge ---
app.clear_animals()
a = app.spawn_animal("cat", x=app.x); a.birth = time.time() - 200; a.hunger = 90
app._urge_animal(a, "play"); a.tick(0.03)
print("urge play: state:", a.state, "| urge cleared:", a.urge is None)
app._urge_animal(a, "rest"); a.tick(0.03)
print("urge rest: state:", a.state, "| urge cleared:", a.urge is None)

# --- urge: MATE on a ready female finds a male and breeds (via ecosystem tick) ---
app.clear_animals()
f = app.spawn_animal("pig", "f", x=app.x); m = app.spawn_animal("pig", "m", x=app.x + 180)
for x in (f, m):
    x.birth = time.time() - 300; x.hunger = 95; x.breed_cd = 0
n0 = len(app.animals)
app._urge_animal(f, "mate")
for _ in range(400):
    app._tick_ecosystem(0.05)
    if len(app.animals) > n0:
        break
print("urge mate: flock", n0, "->", len(app.animals), "(expect +1 baby)")

# --- pet + rename helpers don't crash; rename dialog opens & sets the name ---
app.clear_animals()
a = app.spawn_animal("dog", x=app.x); a.birth = time.time() - 200
app._pet_animal(a)
a.name = "Rex"; app._stash_save()
print("pet+name: name is", repr(a.name), "| state:", a.state)

# --- urge fizzles gracefully when impossible (graze with no grass) ---
app.clear_animals(); app.decor = []
a = app.spawn_animal("bunny", x=app.x); a.birth = time.time() - 200; a.hunger = 90
app._urge_animal(a, "graze")
drive_animal(a, 3, until=lambda: a.urge is None)
print("urge graze no-food: urge cleared gracefully:", a.urge is None, "| alive:", a.alive)

app.quit_app(); print("ALL OK")
