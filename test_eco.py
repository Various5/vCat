import time, vcat
vcat.set_dpi_aware()
st=vcat.load_state(); st["decor"]=[]; st["messes"]=[]; st["animals"]=[]
app=vcat.VCat(st); app.update()
app.next_mouse=app.next_bird=time.monotonic()+9999; app.chase_cd=9999
def drive(sec, until=None):
    t0=time.monotonic()
    while time.monotonic()-t0<sec:
        app.update()
        if until and until(): break
        time.sleep(0.01)

# --- grazing: hungry herbivore eats grass ---
grass=vcat.Decor(app,"grass",app.x+100); app.decor.append(grass)
goat=app.spawn_animal("goat", x=app.x+90); goat.birth=time.time()-200  # adult
goat.hunger=20.0; grass.lushness=100.0
h0=goat.hunger
drive(6, until=lambda: goat.hunger>h0+15)
print("graze: goat hunger", round(h0),"->",round(goat.hunger),"| grass lushness",round(grass.lushness))

# --- hunting: carnivore eats herbivore (hardcore death) ---
app.clear_animals()
prey=app.spawn_animal("bunny", x=app.x+60); prey.birth=time.time()-200; prey.hunger=80
pred=app.spawn_animal("fox", x=app.x-60); pred.birth=time.time()-200; pred.hunger=15
n0=len(app.animals)
drive(8, until=lambda: prey.dying or not prey.alive)
print("hunt: prey dying/dead:", prey.dying or not prey.alive, "| pred hunger:", round(pred.hunger))
drive(3)
print("after death: flock size:", len(app.animals), "(prey removed)")

# --- breeding: well-fed adult pair makes a baby (genes) ---
app.clear_animals()
m=app.spawn_animal("cow","m", x=app.x); f=app.spawn_animal("cow","f", x=app.x+30)
for a in (m,f): a.birth=time.time()-300; a.hunger=95; a.breed_cd=0
drive(8, until=lambda: len(app.animals)>2)
print("breed: flock size now", len(app.animals), "(expect 3: parents + baby)")
babies=[a for a in app.animals if (time.time()-a.birth)<5]
if babies:
    b=babies[0]; print("  baby species:", b.species, "genes pal K:", b.genes['pal'].get('K'), "shiny:", b.genes.get('shiny'))

# --- persistence round-trip ---
app._stash_save(); st2=vcat.load_state()
print("save round-trip: animals saved:", len(st2["animals"]))
app.quit_app(); print("ALL OK")
