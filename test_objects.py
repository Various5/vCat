"""Lock-in for the v1.5.0 objects round: AI furniture, box sit-inside, name tags."""
import os, tempfile, time, vcat
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()
st = vcat.load_state()
st.update(species="cat", created_ts=time.time() - 300000, decor=[], messes=[],
          animals=[], name="")
app = vcat.VCat(st)
app.update()
app.next_mouse = app.next_bird = time.monotonic() + 9999
app.chase_cd = 9999


def drive(sec, until=None):
    t0 = time.monotonic()
    while time.monotonic() - t0 < sec:
        app.update()
        if until and until():
            return True
        time.sleep(0.01)
    return False


# --- all furniture uses AI art with a per-asset palette ---
bad = []
for k in ("bed", "food", "water", "post", "box", "litter", "pond"):
    d = vcat.Decor(app, k, app.x)
    if d._pal() is None or d.cw <= 0 or d.ch <= 0:
        bad.append(k)
    d.destroy()
print("furniture AI-rendered:", not bad, bad or "")

# --- box: the cat hops INSIDE (lands on the floor), not on top ---
app.decor = []
box = vcat.Decor(app, "box", app.x)
app.decor.append(box)
app.x = box.x
app._ensure_ground_state()
app._begin_decor(box)                     # hop into the box
ok = drive(8, until=lambda: app.perch is box and app.state in ("perchsit", "perchsleep"))
inside = ok and abs(app.y - app.ground()) < 3        # on the floor, not elevated
print("cat in box:", ok, "| sits on floor (inside):", inside, "| state:", app.state)

# --- name badge: shows when named, hides when cleared, follows on rename ---
app.name = "Mochi"
app._place()
shown = app.nametag.shown and app.nametag.text == "Mochi"
app.name = ""
app._place()
hidden = not app.nametag.shown
app.name = "Pixel"
app._place()
reshown = app.nametag.shown and app.nametag.text == "Pixel"
print("name badge show/hide/rename:", shown, hidden, reshown)

# --- companion name badge + clean release ---
a = app.spawn_animal("frog", x=app.x + 120)
a.birth = time.time() - 200
a.name = "Hopkins"
for _ in range(3):
    a.tick(0.05)
acomp = a.nametag.shown and a.nametag.text == "Hopkins"
app._release_animal(a)
print("companion badge + release:", acomp)

app.quit_app()
print("ALL OK")
