# brand: the one place to rebrand this base for a new app. The placeholder art
# (tools/make_assets.py) and the "School Colors" preset take their words and colours from here.
# To rebrand: edit this file, then run   .\.venv\Scripts\python.exe tools\make_assets.py


def bgr(hex_colour):
    # '#RRGGBB' -> (blue, green, red), the order OpenCV uses
    value = hex_colour.lstrip('#')
    r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


NAME = 'PHOTO BOOTH'              # the classic frame's caption and the court background
FULL_NAME = 'Fun Image Magic'     # smaller text on the instant-photo, film-strip and corner frames
SHORT_NAME = 'FUN'                # a few letters: the frame badge, trophy, pennant and film edge
CHEER = 'SAY CHEESE!'             # the cheer frame, the hand-held sign, the speech bubble, spotlights

PRIMARY = bgr('#0F766E')          # the main colour (teal): borders, signs, the mascot
ACCENT = bgr('#FFD166')           # the highlight (sunflower): captions and trims
DARK = bgr('#1E293B')             # a deep shade (slate): dark backgrounds and outlines
EXTRAS = [bgr('#118AB2'), bgr('#06D6A0'), bgr('#EF476F')]   # more colours for stripes and confetti
