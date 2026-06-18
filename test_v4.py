import time, vcat

vcat.set_dpi_aware()
state = vcat.load_state()
state["decor"] = []
app = vcat.VCat(state)
app.update()
app.next_mouse = time.monotonic() + 9999
app.chase_cd = 9999

def drive(sec, until=None):
    seen = []
    t0 = time.monotonic()
    while time.monotonic() - t0 < sec:
        app.update()
        if app.state not in seen[-1:]:
            seen.append(app.state)
        if until and until():
            break
        time.sleep(0.012)
    return seen

g = app.ground()
# place one of each decor near the cat
for k in ("bed","food","water","post","plant","box"):
    app.decor.append(vcat.Decor(app, k, app.x))
print("decor placed:", [d.kind for d in app.decor])

# --- drive each interaction by forcing the target ---
results = {}
for kind in ("food","water","post","plant","bed","box"):
    d = next(dd for dd in app.decor if dd.kind == kind)
    app.needs["hunger"] = 30; app.needs["thirst"] = 30
    app.set_state("idle","idle",0.1)
    app.behavior_cd["decor"] = 0
    app.decor_target = None
    app.walk_target = d.x - 14*app.scale if kind in ("post","plant") else d.x
    app.after_walk = ("decor", d)
    app.set_state("walk","walk",30)
    h0, t0_ = app.needs["hunger"], app.needs["thirst"]
    seen = drive(8, until=lambda: app.state in ("groom","perchsit","perchsleep","sleep","scratch","plantbat","munch"))
    # let the interaction run a bit
    seen += drive(2)
    results[kind] = (seen, app.perch is not None, app.needs["hunger"]>h0+10, app.needs["thirst"]>t0_+10)
    print(f"  {kind:6} states={'->'.join(seen[-5:]):40} perch={app.perch is not None} "
          f"hungerUp={app.needs['hunger']>h0+10} thirstUp={app.needs['thirst']>t0_+10}")

# box perch hop-off
app.set_state("perchsit","idle",0.05)
seen = drive(6, until=lambda: app.perch is None and app.state=="idle")
print("box hop-off ->", "->".join(seen[-4:]), "perch=", app.perch)

# --- angry fall ---
app.set_state("idle","idle",1)
app.y = g
app.start_angry_fall()
seen = drive(6, until=lambda: app.state=="idle")
print("angry fall states:", "->".join(seen))

# remove + clear
app.remove_decor(app.decor[0]); print("after remove:", len(app.decor))
app.clear_decor(); print("after clear:", len(app.decor))
app.quit_app()
print("ALL OK")
