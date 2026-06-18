"""Build vcat.ico from the cat's sit sprite (dev/build helper)."""
from PIL import Image

from vcat import FRAMES, PAL, KEY


def render(rows, px):
    w, h = len(rows[0]), len(rows)
    img = Image.new("RGBA", (w * px, h * px), (0, 0, 0, 0))
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            color = PAL[ch]
            if color == KEY:
                continue
            rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
            for dy in range(px):
                for dx in range(px):
                    img.putpixel((c * px + dx, r * px + dy), rgb + (255,))
    return img


def main():
    rows = FRAMES["sit"]
    # crop to the cat with a little margin, keep it square
    art = render(rows, 10)  # 260 x 200
    box = art.getbbox()
    art = art.crop(box)
    side = max(art.size) + 20
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(art, ((side - art.width) // 2, side - art.height - 4))
    sq.save("vcat_icon_preview.png")
    sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    sq.resize((256, 256), Image.NEAREST).save("vcat.ico", sizes=sizes)
    print("wrote vcat.ico")


if __name__ == "__main__":
    main()
