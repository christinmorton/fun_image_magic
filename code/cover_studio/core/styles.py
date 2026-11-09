# styles: each region's look as prompt pieces for the image AI, taken from the style
# guides in docs/merch-styles/. A prompt is the style's base + one scene + the person +
# room for the lettering. The pieces describe colours, objects, light and layout; they
# never name an artist, album, label or design studio, and always ask for no text,
# because the lettering is drawn by the app.
from dataclasses import dataclass


NO_FIRE = 'No fire or flames anywhere in the picture.'


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
    # the base goes with every scene, so it mustn't mention fire: when it said "fire orange"
    # and "firelight", flames turned up in every scene. Scenes that want fire ask for it;
    # the others say "no fire"
    base=('A square late-1990s Southern rap album cover artwork, made as a glossy digital photo collage '
          'with an airbrushed finish. Oversaturated warm colours, mostly deep gold, burnt orange, red and '
          'black. Hard cut-out edges with a soft glowing halo around the person, sparkle glints and lens '
          'flares, dramatic warm lighting. Maximalist and luxurious, every part of the picture full of detail. '
          'No text, no letters, no numbers, no logos, no stickers.'),
    scenes={
        'inferno': ('Inferno',
                    'The person stands in front of a huge wall of flames inside a grand, ornate gold palace '
                    'library that is on fire. Gold jewellery and banknotes fly through the air. Everything '
                    'glows orange and yellow.'),
        'boss_office': ('Boss office',
                        'The person leans back in a large leather chair behind a polished wooden desk covered '
                        'in stacks of cash. Behind them: red velvet walls with gold patterns, a crystal '
                        'chandelier, brass candlesticks and a glass of champagne. ' + NO_FIRE),
        'mansion_life': ('Mansion life',
                         'The person poses in a white and gold marble mansion, holding a phone to their ear. '
                         'Beside them, a large champagne bottle and an ornate gold picture frame. A classic '
                         'cream-coloured luxury car with no badges or logos is parked in front. ' + NO_FIRE),
        'war_zone': ('War zone',
                     'The person stands in front of a battlefield at sunset: huge orange explosions, smoke, '
                     'fighter jets and helicopters in the sky, and a tank behind them. The person wears '
                     'camouflage. No weapons in anyone\'s hands.'),
        'block_at_dusk': ('Block at dusk',
                          'The person stands on a neighbourhood street at dusk under a dramatic orange and '
                          'purple sky, with shotgun houses, warm streetlights and the neon glow of a corner '
                          'store behind them. ' + NO_FIRE),
    },
    layout_space=('Keep the top fifth and the bottom fifth of the picture as background only, with no faces '
                  'or important objects, so lettering can be added later.'),
)

STYLES = {style.key: style for style in [NEW_ORLEANS]}

KEEP_LIKENESS = ('Keep their face, skin tone, hair, facial hair and features exactly as in the photos, so '
                 'they are clearly recognisable.')

# what the person can wear (from the style guide). Jewellery is always a choice: without
# it the AI adds gold chains on its own. Grills and sunglasses change how someone looks,
# so they're opt-in
CLOTHING = {
    'gold_silk': 'a patterned gold and black silk shirt, open at the collar',
    'white_tee': 'a crisp oversized white tee',
    'white_shirt': 'an oversized white button-up shirt',
    'camo': 'a camouflage jacket',
    'tracksuit': 'a velour tracksuit',
    'fur_coat': 'a long fur coat over a black shirt',
    'own': 'the same clothes as in the photos',
}
JEWELLERY = {
    'rope_chain': 'a thick gold rope chain',
    'link_chain': 'a big gold link chain',
    'pendant': 'a large iced-out pendant in a simple star shape, with no letters or logos',
    'rings': 'gold rings on several fingers',
    'watch': 'a big iced-out watch',
    'grills': 'gold teeth (grills) in a slight smile',
}
ACCESSORIES = {
    'sunglasses': 'dark sunglasses',
    'bandana': 'a bandana tied around the head',
    'durag': 'a silk du-rag',
}


def wardrobe(clothing='gold_silk', jewellery=(), accessories=()):
    # the clothing, jewellery and accessories sentences of a prompt
    sentences = [f'They wear {CLOTHING[clothing]}.']
    pieces = [JEWELLERY[j] for j in jewellery] + [ACCESSORIES[a] for a in accessories]
    if pieces:
        sentences.append('They wear ' + (', '.join(pieces[:-1]) + ' and ' + pieces[-1] if len(pieces) > 1 else pieces[0]) + '.')
    if not jewellery:
        sentences.append('They wear no jewellery at all: no chains, rings or watches.')
    return ' '.join(sentences)


def person(references):
    # how to use the reference photos: one photo, or the same person from several angles
    if references <= 1:
        intro = 'The person in the reference photo'
    else:
        intro = (f'The {references} reference photos show the same person from different angles (straight on '
                 'and turned to each side); this person')
    return (f'{intro} is the main figure, waist-up, in the centre, facing the viewer with a confident '
            f'expression. {KEEP_LIKENESS}')

def build_prompt(style, scene, references=1, extras='', clothing=None, jewellery=(), accessories=()):
    # the full prompt for one scene of a style, for `references` photos of the person.
    # clothing / jewellery / accessories are keys of CLOTHING, JEWELLERY and ACCESSORIES
    # (with clothing=None the AI chooses, as in the likeness test); extras adds any other
    # sentence, e.g. 'They hold a microphone.'
    if isinstance(style, str):
        style = STYLES[style]
    if scene not in style.scenes:
        raise ValueError(f'unknown scene "{scene}"; use one of {list(style.scenes)}')
    worn = wardrobe(clothing, jewellery, accessories) if clothing else ''
    parts = [style.base, style.scenes[scene][1], person(references), worn, extras.strip(), style.layout_space]
    return ' '.join(part for part in parts if part)
