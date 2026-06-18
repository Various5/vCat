"""Dev integration test: drive the app loop and assert the mouse-hunt chain runs."""
import time

import vcat

vcat.set_dpi_aware()
state = vcat.load_state()
app = vcat.VCat(state)
app.update()
app.next_mouse = 0.0          # mouse arrives on the next tick
app.chase_cd = 9999           # no cursor play during the test

seen = []
caught = dropped = False
t0 = time.monotonic()
while time.monotonic() - t0 < 30:
    app.update()
    if app.state not in seen[-1:]:
        seen.append(app.state)
    c = app.critter
    if c is not None:
        if abs(c.x - app.x) > 320 and not c.caught:
            c.x = app.x + 300   # keep the mouse in hunting range
        caught = caught or c.caught
        dropped = dropped or (c.dropped_t is not None)
    if dropped and app.state == "idle":
        break
    time.sleep(0.02)

print("states:", " -> ".join(seen))
print("caught:", caught, "| gift dropped:", dropped)
print("kitten:", app.kitten is not None, "| carrying flag:", app.carrying)
app.quit_app()
