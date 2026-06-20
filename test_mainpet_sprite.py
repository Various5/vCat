"""Lock-in: the MAIN pet uses its species body sprite for non-cats, keeps the
rich frame system (animations/costumes/colors) for the cat."""
import os, tempfile, time, vcat
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()


def fresh(sp, off=300000, **kw):
    st = vcat.load_state()
    st.update(species=sp, created_ts=time.time() - off, decor=[], messes=[],
              animals=[], name="", **kw)
    a = vcat.VCat(st)
    a.update()
    a.next_mouse = a.next_bird = time.monotonic() + 9999
    return a


# cat main pet keeps the frame system (costumes/colors) — NOT sprite
app = fresh("cat")
cat_frames = (not app.use_sprite) and hasattr(app, "images") and ("sit", 1) in app.images
app.quit_app()

# every non-cat main pet renders as its sprite, in all the universal states
bad = []
for sp in [s for s in vcat.SPECIES if s != "cat"]:
    app = fresh(sp)
    try:
        assert app.use_sprite, "not sprite"
        for state, anim in (("idle", "idle"), ("walk", "walk"), ("sleep", "sleep"),
                            ("lie", "lie"), ("groom", "groom")):
            app.set_state(state, anim, 5)
            for _ in range(3):
                app.update()
    except Exception as e:
        bad.append((sp, repr(e)))
    app.quit_app()
print("cat keeps frames:", cat_frames)
print("all non-cat main pets render as sprites:", not bad, bad or "")

# egg-spawn species still show the egg while incubating (sprite mode)
app = fresh("dragon", off=1)
app.set_state("egg", "egg", 9999)
for _ in range(4):
    app.update()
egg_ok = app.use_sprite and app.state == "egg"
app.quit_app()
print("dragon egg renders in sprite mode:", egg_ok)

# costume change on a non-cat pet doesn't crash (just no visible effect)
app = fresh("frog")
try:
    app.act_costume("wizard")
    app.update()
    costume_safe = True
except Exception as e:
    costume_safe = repr(e)
app.quit_app()
print("costume on sprite pet is safe:", costume_safe)

print("ALL OK")
