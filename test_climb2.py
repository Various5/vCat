import time, random, vcat
vcat.set_dpi_aware()
state = vcat.load_state(); state["decor"]=[]
app = vcat.VCat(state); app.update()
app.next_mouse=time.monotonic()+9999; app.chase_cd=9999

cands = app.climb_targets()
print("climb candidates:", len(cands))
for hwnd,(l,t,r,b) in cands:
    import ctypes
    buf=ctypes.create_unicode_buffer(80); vcat.user32.GetWindowTextW(hwnd,buf,80)
    print(f"   '{buf.value[:30]:30}' rect=({l},{t},{r},{b})")

app.behavior_cd["climb"]=0
_r=random.random; random.random=lambda:0.0
app.do_go_climb()
random.random=_r
print("after do_go_climb: state=",app.state,"after_walk=",app.after_walk)

seen=[]; ys=[]
t0=time.monotonic()
while time.monotonic()-t0<25:
    app.update()
    if app.state not in seen[-1:]: seen.append(app.state)
    if app.state=="wallclimb": ys.append(round(app.y))
    if app.surface_hwnd is not None: break
    time.sleep(0.012)
print("states:", "->".join(seen))
print("climb y (top->down sample):", ys[::15][:8], "...", ys[-1] if ys else None)
print("landed on window:", app.surface_hwnd is not None, "| y=",round(app.y),"ground=",round(app.ground()))

# now simulate the user yanking that window -> angry fall
if app.surface_hwnd is not None:
    app.set_state("idle","idle",5)
    # fake a big jump in the tracked rect
    l,t,r,b = app.surface_last
    app.surface_last = (l+200, t, r+200, b)   # pretend it moved 200px
    app.surface_move = 0
    s2=[]; t0=time.monotonic()
    while time.monotonic()-t0<5:
        app.update()
        if app.state not in s2[-1:]: s2.append(app.state)
        if app.state=="idle" and "mad" in s2: break
        time.sleep(0.012)
    print("after window yank:", "->".join(s2))
app.quit_app()
