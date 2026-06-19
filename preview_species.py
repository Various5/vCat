"""Visual preview: every species' head (ears+muzzle) + the new vegetation variants."""
import math
from PIL import Image, ImageDraw
import vcat as v

PX = 7
PAD = 10
LABEL_H = 16


def grid_size(grid):
    return len(grid[0]), len(grid)


def draw_grid(d, grid, ox, oy, px=PX):
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch != ".":
                d.rectangle([ox + c * px, oy + r * px,
                             ox + c * px + px - 1, oy + r * px + px - 1],
                            fill=v.PAL[ch])


def build_head(species):
    """The 10x7 front head for a species (ears + muzzle), as the app builds it."""
    ears = v.SPECIES_EARS.get(species, v.SPECIES_EARS["cat"])
    faces = v._faces_for(v.SPECIES_FACE[species]) if species in v.SPECIES_FACE else None
    head = v._heads_for(ears, faces)[0]
    return head


def section(title, items, cols, px=PX):
    """items: list of (label, grid). Returns a PIL image of the grid block."""
    cell_w = max(grid_size(g)[0] for _, g in items) * px + 2 * PAD
    cell_h = max(grid_size(g)[1] for _, g in items) * px + LABEL_H + PAD
    rows_n = math.ceil(len(items) / cols)
    img = Image.new("RGB", (cols * cell_w, rows_n * cell_h + LABEL_H), "#6a8aa8")
    d = ImageDraw.Draw(img)
    d.text((6, 3), title, fill="white")
    for i, (label, grid) in enumerate(items):
        ox = (i % cols) * cell_w + PAD
        oy = (i // cols) * cell_h + LABEL_H + LABEL_H
        d.text((ox, oy - 13), label, fill="white")
        draw_grid(d, grid, ox, oy, px)
    return img


def stack(images, gap=8):
    w = max(im.width for im in images)
    h = sum(im.height for im in images) + gap * (len(images) - 1)
    out = Image.new("RGB", (w, h), "#41566a")
    y = 0
    for im in images:
        out.paste(im, (0, y))
        y += im.height + gap
    return out


heads = [(sp, build_head(sp)) for sp in v.SPECIES]
veg = []
for kind, variants in v.VEG_VARIANTS.items():
    for i, g in enumerate(variants):
        veg.append((f"{kind}{i}", g))
prey = [("mouse", v.CRITTER_FRAMES["mouse1"]), ("bug", v.CRITTER_FRAMES["bug1"]),
        ("bird", v.BIRD_FRAMES["up"])]

img = stack([
    section("SPECIES FACES (ears + muzzle/beak)", heads, cols=7),
    section("VEGETATION VARIANTS", veg, cols=6, px=6),
    section("PREY", prey, cols=6),
])
img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
img.save("preview_species.png")
print("wrote preview_species.png", img.size)
