# styles: each region's look as prompt pieces for the image AI, taken from the style
# guides in docs/merch-styles/. A prompt is the style's base + one scene + the person +
# room for the lettering. The pieces describe colours, objects, light and layout; they
# never name an artist, album, label or design studio, and always ask for no text,
# because the lettering is drawn by the app.
from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    key: str
    name: str
    base: str               # always used: the era, finish and colours, and "no text"
    scenes: dict            # scene key -> (name, description)
    layout_space: str       # keeps the top and bottom clear for the lettering


NEW_ORLEANS = Style(
    key='new_orleans',
    name='New Orleans, 1996-2001',
    base=('A square late-1990s Southern rap album cover artwork, made as a glossy digital photo collage '
          'with an airbrushed finish. Oversaturated warm colours, mostly gold, fire orange, red and black. '
          'Hard cut-out edges with a soft glowing halo around the person, sparkle glints and lens flares, '
          'dramatic firelight. Maximalist and luxurious, every part of the picture full of detail. '
          'No text, no letters, no numbers, no logos, no stickers.'),
    scenes={
        'inferno': ('Inferno',
                    'The person stands in front of a huge wall of flames inside a grand, ornate gold palace '
                    'library that is on fire. Gold jewellery and banknotes fly through the air. Everything '
                    'glows orange and yellow.'),
        'boss_office': ('Boss office',
                        'The person leans back in a large leather chair behind a polished wooden desk covered '
                        'in stacks of cash. Behind them: red velvet walls with gold patterns, a crystal '
                        'chandelier, brass candlesticks and a glass of champagne.'),
        'mansion_life': ('Mansion life',
                         'The person poses in a white and gold marble mansion, holding a phone to their ear. '
                         'Beside them, a large champagne bottle and an ornate gold picture frame. A classic '
                         'cream-coloured luxury car with no badges or logos is parked in front.'),
        'war_zone': ('War zone',
                     'The person stands in front of a battlefield at sunset: huge orange explosions, smoke, '
                     'fighter jets and helicopters in the sky, and a tank behind them. The person wears '
                     'camouflage. No weapons in anyone\'s hands.'),
        'ghetto_skyline': ('Ghetto skyline',
                           'The person stands in front of a neighbourhood street at dusk under a dramatic '
                           'orange and purple sky, with flames rising across the foreground.'),
    },
    layout_space=('Keep the top fifth and the bottom fifth of the picture as background only, with no faces '
                  'or important objects, so lettering can be added later.'),
)

STYLES = {style.key: style for style in [NEW_ORLEANS]}

KEEP_LIKENESS = ('Keep their face, skin tone, hair, facial hair and features exactly as in the photos, so '
                 'they are clearly recognisable.')


def person(references):
    # how to use the reference photos: one photo, or the same person from several angles
    if references <= 1:
        intro = 'The person in the reference photo'
    else:
        intro = (f'The {references} reference photos show the same person from different angles (straight on '
                 'and turned to each side); this person')
    return (f'{intro} is the main figure, waist-up, in the centre, facing the viewer with a confident '
            f'expression. {KEEP_LIKENESS}')

def build_prompt(style, scene, references=1, extras=''):
    # the full prompt for one scene of a style, for `references` photos of the person.
    # extras adds clothing or jewellery choices, e.g. 'They wear a gold rope chain.'
    if isinstance(style, str):
        style = STYLES[style]
    if scene not in style.scenes:
        raise ValueError(f'unknown scene "{scene}"; use one of {list(style.scenes)}')
    parts = [style.base, style.scenes[scene][1], person(references), extras.strip(), style.layout_space]
    return ' '.join(part for part in parts if part)
