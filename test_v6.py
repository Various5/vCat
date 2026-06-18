import time, vcat
vcat.set_dpi_aware()
st = vcat.load_state(); st["decor"]=[]; st["messes"]=[]; st["created_ts"]=None
app = vcat.VCat(st); app.update()
app.next_mouse=app.next_bird=time.monotonic()+9999; app.chase_cd=9999

def drive(sec, until=None):
    seen=[]; t0=time.monotonic()
    while time.monotonic()-t0<sec:
        app.update()
        if app.state not in seen[-1:]: seen.append(app.state)
        if until and until(): break
        time.sleep(0.012)
    return seen

print("migrated existing -> stage:", app.stage, "scale:", app.scale, "(expect adult)")

# DRAGON egg hatch
app.begin_new_pet("dragon"); app.update()
print("dragon born -> stage:", app.stage, "state:", app.state, "scale:", round(app.scale,2))
assert app.stage=="egg" and app.state=="egg"
app.created_ts = time.time() - (vcat.EGG_DUR + 1)   # fast-forward past incubation
seen = drive(4, until=lambda: app.state=="idle" and app.stage=="baby")
print("  hatch chain:", "->".join(seen), "| stage:", app.stage, "scale:", round(app.scale,2))

# grow baby -> kid -> teen -> adult, checking scale increases + birthdays
sizes={}
for stg, age in (("baby",10),("kid",2000),("teen",8000),("adult",30000),("elder",400000)):
    app.created_ts = time.time() - vcat.EGG_DUR - age
    drive(1.0)
    sizes[stg]=round(app.scale,2)
print("  scale by stage:", sizes)
assert sizes["baby"]<sizes["kid"]<=sizes["teen"]<sizes["adult"], "growth not monotonic"

# PASSING + rebirth (mortal)
app.immortal=False
app.species="dog"; app.created_ts = time.time() - 700000  # well past elder bound
old_created = app.created_ts
seen = drive(7, until=lambda: app.created_ts != old_created)  # rebirth resets created_ts
print("  passing->rebirth states:", "->".join(seen), "| new species:", app.species, "stage:", app.stage)

# immortal: never passes
app.immortal=True; app.created_ts=time.time()-999999
print("  immortal at huge age -> stage:", app.life_stage(), "(expect elder)")

# STORK species born as baby
app.begin_new_pet("bunny"); app.update()
print("bunny (stork) -> stage:", app.stage, "stork:", app.stork is not None)

# persistence round-trip
app.species="fox"; app.created_ts=time.time()-5000; app.immortal=False; app.base_scale=4
app._stash_save()
st2=vcat.load_state()
print("save round-trip: species", st2["species"], "scale", st2["scale"], "immortal", st2["immortal"], "created set:", st2["created_ts"] is not None)
app.quit_app(); print("ALL OK")
