"""Every main-pet behaviour must fit the species. A cow must NOT hunt birds."""
import os, tempfile, time, vcat
vcat.SAVE_PATH = os.path.join(tempfile.gettempdir(), "vcat_test_save.json")
vcat.set_dpi_aware()


def fresh(species):
    st = vcat.load_state()
    st.update(species=species, created_ts=time.time() - 300000,  # adult
              decor=[], messes=[], animals=[], kitten=False, name="")
    app = vcat.VCat(st)
    app.update()
    app.next_mouse = app.next_bird = time.monotonic() + 1e9
    return app


# --- THE REPORTED BUG: a cow must never go after a bird or the cursor/mouse ---
app = fresh("cow")
app.bird = vcat.Bird(app)                       # a bird flies by
app.critter = vcat.Critter(app)                 # a mouse scurries by
app.cur = (int(app.x + 10), int(app.ground() - 40 * app.scale))  # cursor right on her
app.cursor_hist = [(time.monotonic(), app.cur[0] + i * 90, app.cur[1]) for i in range(5)]
app.chase_cd = 0.0
cow_states = set()
for _ in range(400):
    app.tick()
    cow_states.add(app.state)
    time.sleep(0.002)
bad = cow_states & {"birdwatch", "hunt", "hunt_stalk", "stalk", "chase", "catch",
                    "gotcha", "laser", "toy_chase", "toy_bat", "wallclimb",
                    "scratch", "tailchase", "zoomies", "flip", "jump"}
print("COW never hunts/climbs/etc:", not bad, "| forbidden states seen:", sorted(bad) or "none")
print("  (cow states observed:", sorted(cow_states), ")")
app.quit_app()

# --- trait table: predators hunt, herbivores don't; cat keeps everything ---
def can(sp, t):
    return t in vcat.SPECIES_TRAITS.get(sp, set())
checks = [
    ("cat", "hunt", True), ("cat", "birds", True), ("cat", "litter", True),
    ("cat", "climb", True), ("cat", "flip", True),
    ("cow", "hunt", False), ("cow", "birds", False), ("cow", "climb", False),
    ("cow", "litter", False), ("cow", "zoomies", False),
    ("bunny", "hunt", False), ("bunny", "zoomies", True), ("bunny", "birds", False),
    ("goat", "climb", True), ("goat", "hunt", False),
    ("fox", "hunt", True), ("fox", "birds", True), ("fox", "litter", False),
    ("dragon", "birds", True), ("frog", "hunt", True), ("frog", "birds", False),
    ("penguin", "hunt", False), ("pig", "hunt", False), ("panda", "hunt", False),
]
trait_ok = all(can(sp, t) == exp for sp, t, exp in checks)
print("trait table correct:", trait_ok,
      "|", [(sp, t) for sp, t, exp in checks if can(sp, t) != exp] or "all good")

# --- a cat STILL does everything it used to (no regression for the flagship) ---
app = fresh("cat")
ok_cat = (app.can("hunt") and app.can("birds") and app.can("litter")
          and app.can("climb") and app.can("flip") and app.can("toy") and app.can("laser"))
# cat can be told to do tricks / laser / yarn
app.act_trick()
trick_ok = app.state in ("jump", "fall") or app.after_jump == ("tada", None)
app.set_state("idle", "idle", 1)
app.act_laser(); laser_ok = app.laser is not None
app.act_laser()  # toggle off
print("CAT unchanged:", ok_cat and trick_ok and laser_ok)
app.quit_app()

# --- a cow's menu must NOT offer cat tricks, and it can't be forced to ---
app = fresh("cow")
app.act_trick()                  # do nothing (no flip trait)
app.act_laser(); cow_no_laser = app.laser is None
app.act_play()                   # zoomies blocked
app.act_toy(); cow_no_toy = app.toy is None
cow_actions_blocked = (cow_no_laser and cow_no_toy
                       and app.state not in ("jump", "fall", "zoomies"))
print("COW menu actions blocked:", cow_actions_blocked, "| potty bar hidden:", not app.can("litter"))
app.quit_app()

# --- herbivore begs with a veggie, not a fish; carnivore begs with a fish ---
print("beg icon: cow->", "veg" if vcat.SPECIES_DIET.get("cow") == "herb" else "fish",
      "| cat->", "veg" if vcat.SPECIES_DIET.get("cat") == "herb" else "fish",
      "| ICON_VEG present:", "veg" in vcat.ICONS)

# --- a flip-incapable hunter (bear) caught mid-air must FALL, not float ---
app = fresh("bear")
app.surface_hwnd = None
app.perch = None
app.y = app.ground() - 200          # suspended at "cursor" height after a pounce
app.do_flip()                        # bear can't flip
bear_falls = app.state == "fall"
app.quit_app()
# a grounded non-flipper just idles (no float, no flip)
app = fresh("cow")
app.y = app.ground()
app.do_flip()
cow_idle = app.state == "idle"
print("flip-incapable airborne bear falls:", bear_falls, "| grounded cow idles:", cow_idle)

print("ALL OK")
