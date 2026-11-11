"""Generate src/scrollcapture/resources/icon.ico (+ icon.png) with Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "src" / "scrollcapture" / "resources"
S = 1024


def draw() -> Image.Image:
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, S - 40, S - 40), radius=210, fill=(47, 111, 237, 255))
    # long page
    d.rounded_rectangle((300, 150, 724, 690), radius=44, fill=(255, 255, 255, 255))
    for i, y in enumerate(range(235, 640, 80)):
        w = 320 if i % 3 != 2 else 210
        d.rounded_rectangle((355, y, 355 + w, y + 32), radius=16, fill=(196, 212, 245, 255))
    # capture frame corners
    c, t, L = (255, 204, 0, 255), 40, 130
    for (x, y, sx, sy) in ((210, 110, 1, 1), (814, 110, -1, 1), (210, 730, 1, -1), (814, 730, -1, -1)):
        d.line([(x, y + sy * L), (x, y), (x + sx * L, y)], fill=c, width=t, joint="curve")
    # down arrow
    d.rectangle((482, 760, 542, 840), fill=(255, 255, 255, 255))
    d.polygon([(512, 935), (417, 830), (607, 830)], fill=(255, 255, 255, 255))
    return im


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    im = draw()
    im.resize((256, 256), Image.LANCZOS).save(OUT / "icon.png")
    im.save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("written", OUT)


if __name__ == "__main__":
    main()
