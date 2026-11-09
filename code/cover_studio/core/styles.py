# styles: each region's look as prompt pieces for the image AI, taken from the style
# guides in docs/merch-styles/. A prompt is the style's base + one scene + the person +
# room for the lettering. The pieces describe colours, objects, light and layout; they
# never name an artist, album, label or design studio, and always ask for no text,
# because the lettering is drawn by the app.
import re
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
    # the AI sometimes puts the head right at the top anyway (the lettering screen then
    # moves the artwork down: core/framing.py), so the head's place is spelt out too
    layout_space=('Keep the top fifth and the bottom fifth of the picture as background only, with no faces '
                  'or important objects, so lettering can be added later. The top of the person\'s head must '
                  'be below the top quarter of the picture, with only background above it.'),
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

# the user's own words can add to a scene (details) or replace it (a custom scene). They're
# checked first (check_user_text), and these rules are repeated after them, since the AI
# leans towards whatever it read last
CUSTOM = 'custom'
GUARDRAILS = ('Whatever else is asked for above: no text, letters, numbers, logos, brand names or stickers '
              'anywhere in the picture, and keep the person\'s face exactly like the reference photos.')
MAX_USER_TEXT = 400
# names that must never reach the AI: artists, labels, design studios, albums, the
# Parental Advisory mark, and brands whose logos would end up on merch
BANNED_NAMES = ['no limit', 'cash money', 'pen & pixel', 'pen and pixel', 'master p', 'juvenile', 'lil wayne',
                'hot boys', 'mystikal', 'parental advisory', 'riaa', '400 degreez', 'rolls royce', 'rolls-royce',
                'bentley', 'mercedes', 'lamborghini', 'ferrari', 'rolex', 'cartier', 'gucci', 'louis vuitton',
                'versace', 'chanel', 'prada', 'nike', 'supreme', 'disney', 'marvel']


def check_user_text(text):
    # what's wrong with words a user wants to add to a prompt (empty list = fine). Real
    # people can't all be listed, so famous names other than these aren't caught here
    problems = []
    if len(text) > MAX_USER_TEXT:
        problems.append(f'too long: keep it under {MAX_USER_TEXT} characters')
    lower = f' {re.sub(r"[^a-z0-9&-]+", " ", text.lower())} '
    found = [name for name in BANNED_NAMES if f' {name} ' in lower]
    if found:
        problems.append(f'no real artists, labels or brands: {", ".join(found)}')
    return problems

def sentence(text):
    # the user's words as a finished sentence, so they don't run into the next one
    text = text.strip()
    return text + '.' if text and text[-1] not in '.!?' else text

def build_prompt(style, scene, references=1, extras='', clothing=None, jewellery=(), accessories=(),
                 details='', custom_scene=''):
    # the full prompt for one scene of a style, for `references` photos of the person.
    # clothing / jewellery / accessories are keys of CLOTHING, JEWELLERY and ACCESSORIES
    # (with clothing=None the AI chooses, as in the likeness test); extras adds any other
    # sentence. The user's own words: scene=CUSTOM uses custom_scene as the whole scene,
    # and details are added to any scene
    if isinstance(style, str):
        style = STYLES[style]
    if scene == CUSTOM:
        if not custom_scene.strip():
            raise ValueError('a custom scene needs a description')
        scene_text = sentence(custom_scene)
    elif scene in style.scenes:
        scene_text = style.scenes[scene][1]
    else:
        raise ValueError(f'unknown scene "{scene}"; use one of {list(style.scenes) + [CUSTOM]}')
    worn = wardrobe(clothing, jewellery, accessories) if clothing else ''
    user_words = scene == CUSTOM or details.strip()
    parts = [style.base, scene_text, person(references), worn, sentence(details), extras.strip(), style.layout_space,
             GUARDRAILS if user_words else '']
    return ' '.join(part for part in parts if part)
