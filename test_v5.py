import time, vcat
vcat.set_dpi_aware()
st = vcat.load_state(); st["decor"]=[]; st["messes"]=[]
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

# 1) potty WITH a clean litter box -> uses box
lit = vcat.Decor(app,"litter",app.x); app.decor.append(lit)
app.potty=10.0; app.set_state("idle","idle",0.05); app.behavior_cd["decor"]=99
seen=drive(10, until=lambda: app.state=="groom" and app.potty>90)
print("potty(box):", "->".join(seen[-5:]), "| potty=",round(app.potty),"| box.uses=",lit.uses)

# 2) potty with DIRTY box and no clean one -> floor mess
lit.uses=6; app.potty=10.0; app.set_state("idle","idle",0.05)
n0=len(app.messes)
seen=drive(10, until=lambda: len(app.messes)>n0)
print("potty(floor):", "->".join(seen[-5:]), "| messes=",len(app.messes),"| potty=",round(app.potty))

# 3) clean a mess + scoop
if app.messes: app.clean_mess(app.messes[0])
app.scoop_litter(lit)
print("after clean: messes=",len(app.messes),"| box.uses=",lit.uses)

# 4) bird catch (force a low swoop right over the cat)
app.bird = vcat.Bird(app)
app.bird.x = app.x; app.bird.dir=1; app.bird.swoop_t=0.0; app.bird.base_y=app.ground()-180*app.scale
app.set_state("idle","idle",0.05)
seen=drive(8, until=lambda: app.bird is None or app.state=="groom")
print("bird:", "->".join(seen), "| bird gone:", app.bird is None)

# 5) costume + name persistence round-trip
app.act_costume("bat"); app.name="Mittens"
app._stash_save()
st2 = vcat.load_state()
print("save round-trip: name=",repr(st2["name"]),"costume=",st2["costume"],"potty=",round(st2["potty"]))

# 6) screen shake from angry fall
app.set_state("idle","idle",1); app.y=app.ground()
app.start_angry_fall()
drive(3, until=lambda: app.shake>0)
peak=app.shake
drive(3, until=lambda: app.state=="idle")
print("shake peaked:", round(peak,1), "-> settled:", round(app.shake,1))

# 7) treat + come
app.needs["hunger"]=40; app.act_treat(); app.update()
print("treat hunger:", round(app.needs["hunger"]))
app.act_come(); print("come -> state:", app.state)

app.quit_app(); print("ALL OK")
