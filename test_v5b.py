import time, random, vcat
random.seed(3)
vcat.set_dpi_aware()
st = vcat.load_state()
app = vcat.VCat(st); app.update()
# rename dialog opens + OK applies name without error
app.act_rename(); app.update()
ok = app._name_dlg is not None
if ok:
    # simulate typing + confirm by invoking the dialog's entry + Return
    for w in app._name_dlg.winfo_children():
        for e in w.winfo_children():
            if isinstance(e, vcat.tk.Entry):
                e.delete(0,"end"); e.insert(0,"Shadow"); break
    app._name_dlg.event_generate("<Return>"); app.update()
print("rename dialog opened:", ok, "| name now:", repr(app.name), "| dlg closed:", app._name_dlg is None)

# broad stability: kitten + every decor incl litter + costume, randomized, many ticks
app.act_costume("bat")
if not app.kitten: app.act_kitten()
for i,k in enumerate(("bed","food","water","litter","post","plant","box")):
    app.decor.append(vcat.Decor(app,k,250+i*120))
seen=set(); t0=time.monotonic(); n=0
while time.monotonic()-t0<28:
    if n%150==0:
        for k in app.behavior_cd: app.behavior_cd[k]=0.0
        app.potty=random.uniform(8,90); app.needs["hunger"]=random.uniform(15,90)
    if n%500==250: app.next_bird=time.monotonic()  # spawn a bird
    app.update(); seen.add(app.state); n+=1; time.sleep(0.004)
print("ticks:",n,"| states:",len(seen),"|", ",".join(sorted(seen)))
print("messes:",len(app.messes),"decor:",len(app.decor))
app.quit_app()
