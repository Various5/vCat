import time, vcat
vcat.set_dpi_aware()
st = vcat.load_state()
app = vcat.VCat(st); app.update()
if not app.kitten: app.act_kitten()
app.act_costume("wizard")
for i,k in enumerate(("bed","food","litter","box","post")): app.decor.append(vcat.Decor(app,k,300+i*130))
# fox = egg species; raise it from egg through full life smoothly
app.begin_new_pet("fox"); app.update()
born = time.time()
states=set(); stages=[]; n=0; t0=time.monotonic()
LIFE_SECS = 700000  # compress fox's whole life into the test window
while time.monotonic()-t0 < 24:
    # map elapsed test-time to a full lifespan
    frac = (time.monotonic()-t0)/24
    app.created_ts = born - frac*LIFE_SECS
    if app.stage not in [s for s,_ in stages][-1:]:
        stages.append((app.stage, round(app.scale,2)))
    if n%200==0:
        for k in app.behavior_cd: app.behavior_cd[k]=0.0
    app.update(); states.add(app.state); n+=1; time.sleep(0.004)
print("ticks:",n)
print("stages seen:", stages)
print("states:", ",".join(sorted(states)))
app.quit_app()
