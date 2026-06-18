"""Dev integration test: yarn play, laser chase, and backflip chains."""
import time

import vcat

vcat.set_dpi_aware()
state = vcat.load_state()
app = vcat.VCat(state)
app.update()
app.next_mouse = time.monotonic() + 9999   # no mice during this test
app.chase_cd = 9999

def drive(seconds, until=None):
    seen = []
    t0 = time.monotonic()
    while time.monotonic() - t0 < seconds:
        app.update()
        if app.state not in seen[-1:]:
            seen.append(app.state)
        if until and until():
            break
        time.sleep(0.02)
    return seen

# --- yarn ---
app.act_toy()
assert app.toy is not None, "toy spawned"
app.toy.x, app.toy.vx = app.x + 250, 0.0   # park it near the cat
seen = drive(20, until=lambda: app.bat_count >= 1)
print("yarn states:", " -> ".join(seen))
print("bat_count:", app.bat_count, "| toy moving after bat:", app.toy.moving())
app.act_toy()
assert app.toy is None, "toy removed"

# --- laser ---
app.set_state("idle", "idle", 1)
app.act_laser()
assert app.laser is not None, "laser on"
seen = drive(6)
print("laser states:", " -> ".join(seen))
d0 = abs(app.laser.x - app.x)
app.act_laser()
assert app.laser is None, "laser off"
print("laser chase reached state:", "laser" in seen, "| dist to dot:", round(d0))

# --- backflip ---
app.set_state("idle", "idle", 1)
app.act_trick()
seen = drive(3)
print("flip states:", " -> ".join(seen))
print("flip anim used:", any(s == "jump" for s in seen))

app.quit_app()
print("ALL OK")
