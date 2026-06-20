# vCat 🐈‍⬛ — a tiny pixel pet (Tamagotchi) for your desktop

A single little animal that lives on your Windows desktop: it walks the
taskbar, chases your cursor, climbs your windows, plays with toys, makes a
mess if it has no litter box, and **grows up in real time like a Tamagotchi** —
from an egg or a stork delivery, through baby → kid → teen → adult → elder,
and on into a new generation.

It's `vcat.py` (tkinter only) packaged into a single `.exe` with PyInstaller.
Pixel art and 8-bit sounds are generated in code — no binary asset files. The
richer environment art is AI-designed (Stable-Diffusion via ComfyUI), converted
offline into pixel grids and shipped as a generated `vcat_assets.py` module
(plain text); if it's absent the app falls back to hand-drawn vegetation.

## Features

- **14 species** — cat, dog, dragon, bunny, fox, goat, pig, cow, bear, panda,
  frog, penguin, chick, hamster — each with its own ears, **muzzle/beak**,
  colors, voice (meow, woof, roar, oink, moo, baa, ribbit, squeak, yip…) **and
  its own way of moving** — bunnies and frogs *hop*, penguins and pigs *waddle*,
  the dragon *hovers*, cats trot. They also idle with lots of little behaviours
  (look around, groom, stretch, play, nap) so a flock never looks static.
- **Tamagotchi lifecycle** — real-time aging with visible growth, birthday
  celebrations 🎂, a gentle old-age passing 🌈 and rebirth (or an Immortal
  toggle). Dragons/foxes hatch from a wobbling **egg**; mammals arrive by
  **stork** 🪶.
- **Needs & care** — hunger, thirst, love and a bladder. Feed/water/treat her;
  give her a **litter box** or the floor gets messy.
- **Play** — chases the **mouse cursor**, hunts wandering critters (a mouse, a
  brown vole, a white mouse, a scuttling **beetle**) and **birds** that come in
  six colours, a **laser pointer**, a physics **yarn ball** you can fling,
  zoomies, backflips.
- **Windows** — climbs the edges of your real windows and naps on the title
  bar; move the window and she falls off, flips you off with a censored swear,
  and the screen shakes. 🖕
- **Home** — place **AI-designed pixel furniture** (cozy bed, food & water bowls,
  scratching post, litter tray, pond) and a cardboard **box your cat climbs right
  inside** (peeking out the top 📦).
- **Customise** — costumes (batcat 🦇, spidercat 🕷, wizard 🧙, king 👑,
  devil 😈), fur colors, size, and **name your pets** — named pets wear a little
  **name badge** above their head that's also an easy right-click target.
- **A living ecosystem** — add a flock of animals (the old kitten is retired). Plant
  grass, flowers, bushes and trees 🌿🌸🌳 — lush **AI-designed pixel scenery** (oak,
  pine and cherry-blossom trees; leafy, berry and flowering bushes; tulips, daisies
  and wildflowers), each in **random variants** that **grow in real time** from a
  sprout to full size. Herbivores graze grass and browse bushes; carnivores hunt
  herbivores; everyone ages, breeds and (in hardcore mode) can die — a self-sustaining
  food chain that runs even when you're not feeding it.
- **Right-click any animal** for a tidy, per-creature menu: pet it, feed it, and give
  it commands that suit its kind — send a herbivore to **graze**, a carnivore to
  **hunt**, an adult to **find a mate**, or just tell it to **come here / play / rest**.
  Rename or release it. The "add animals" menu is grouped into 🌿 Herbivores and
  🥩 Carnivores (plus a 🎲 *Surprise me*).
- **Breeding & genetics** — males ♂ and females ♀ (females wear a little bow); a
  well-fed adult pair makes a baby that inherits blended colors, with rare rolls for
  ✨shiny variants, special abilities (swift/big/tiny/glow), cross-species hybrids,
  and ultra-rare specials.

Everything is saved in `%APPDATA%\vCat`.

## Run from source

```sh
py -m pip install pyinstaller pillow   # pillow only needed for the icon/sheet
py vcat.py
```

## Build the .exe

```sh
py -m PyInstaller --onefile --noconsole --name vCat --icon vcat.ico \
    --exclude-module PIL --noconfirm vcat.py
```

The build lands in `dist/vCat.exe`. (Prebuilt binaries are attached to each
[Release](../../releases).)

> Windows SmartScreen may warn about the unsigned exe on first launch —
> click *More info → Run anyway*. Antivirus false positives can happen with
> PyInstaller; the full source is right here in `vcat.py`.

---

Made with ❤️ and [Claude Code](https://claude.com/claude-code).
