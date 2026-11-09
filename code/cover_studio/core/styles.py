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
    scenes: dict            # scene key -> (name, description), or (name, description, base) for a
                            # scene with its own look (e.g. Memphis's black-and-white tape era)
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
        'crew_lineup': ('Crew line-up',
                        'The crew stands shoulder to shoulder in a row, from the waist up, lit dramatically from '
                        'below, with smoke, sparks and a fiery orange glow behind them.'),
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

LAYOUT_SPACE = NEW_ORLEANS.layout_space

# the other regions, from docs/merch-styles/memphis.md, houston.md and compton-la.md. Their
# own lettering, layouts and finishes aren't built yet; the artwork already works
MEMPHIS = Style(
    key='memphis',
    name='Memphis, 1993-2001',
    base=('A square late-1990s Memphis underground rap album cover artwork: a dark, gritty, airbrushed '
          'digital photo collage. Low, hard lighting, deep shadows, mostly black with blood red and toxic '
          'green accents. Menacing and raw rather than luxurious. '
          'No text, no letters, no numbers, no logos, no stickers.'),
    scenes={
        'graveyard': ('Graveyard at midnight',
                      'The person stands among old leaning tombstones at midnight, with fog on the ground, bare '
                      'twisted trees, crows and a full moon behind them. ' + NO_FIRE),
        'hellfire': ('Hellfire',
                     'The person stands on a cracked, burning landscape under a blood-red sky, with smoke, '
                     'glowing embers and a crowd of shadowy figures behind them.'),
        'smoke_room': ('Smoke room',
                       'The person stands in a dark room filled with thick smoke, lit only by red light from '
                       'below, with candles on the floor around them.'),
        'back_street': ('Back street (tape era)',
                        'The person stands in an empty back street with a chain-link fence and power lines. '
                        + NO_FIRE,
                        'A square early-1990s underground rap cassette cover: a grainy black-and-white photograph, '
                        'high contrast, shot with a flash on cheap film, as if photocopied. Raw and handmade. '
                        'No text, no letters, no numbers, no logos, no stickers.'),
        'limo_casket': ('Limo and casket',
                        'The person stands at night beside a long white limousine and a polished casket covered '
                        'in flowers, lit like a king\'s funeral. ' + NO_FIRE),
        'crew_mist': ('Crew in the mist',
                      'The crew stands close together in thick fog, wearing hoods and caps, lit from below by red '
                      'light.'),
    },
    layout_space=LAYOUT_SPACE,
)

HOUSTON = Style(
    key='houston',
    name='Houston, 1990s-2005',
    base=('A square mid-1990s Houston rap album cover artwork, made as a glossy digital photo collage. Deep '
          'candy-paint colours, mostly candy purple with chrome, night blue and touches of candy red. Night '
          'lighting with streetlight glow and sharp chrome reflections. Slow, smooth and shining. '
          'No text, no letters, no numbers, no logos, no stickers.'),
    scenes={
        'slab_parade': ('Slab parade',
                        'The person stands in front of a line of classic American luxury sedans in deep candy '
                        'paint at night, with chrome spoke rims poking far out from the wheels and the trunks '
                        'open to show glowing lights, under streetlights. The cars have no badges or logos. '
                        + NO_FIRE),
        'screwed_haze': ('Screwed haze',
                         'The person stands in a surreal, slowed-down purple dream: soft focus, faint double '
                         'images, floating shapes and a glowing lilac sky. ' + NO_FIRE),
        'candy_wave': ('Candy wave',
                       'The person stands beside a candy-painted classic sedan riding a giant ocean wave, with '
                       'spray in the air and a bright sky. The car has no badges or logos. ' + NO_FIRE),
        'ward_at_night': ('Ward at night',
                          'The person stands on a neighbourhood street of small wooden houses under big live oak '
                          'trees, lit by purple streetlights, with a candy-painted sedan at the kerb. ' + NO_FIRE),
        'front_page': ('Front page',
                       'The person is the photo on a newspaper front page: grey columns of blurred lines that '
                       'can\'t be read, smaller photos and empty headline space around them, on off-white '
                       'newsprint. ' + NO_FIRE),
        'behind_fence': ('Behind the fence',
                         'The person stands behind a chain-link fence in hard daylight, shot on grainy film. '
                         + NO_FIRE),
    },
    layout_space=LAYOUT_SPACE,
)

COMPTON_LA = Style(
    key='compton_la',
    name='Compton and LA, 1988-1996',
    base=('A square late-1980s or early-1990s West Coast rap album cover: a street photograph in bright, hazy '
          'California daylight, shot on 35 mm film, with sun-faded colours, strong blacks and a little film '
          'grain. Real and raw rather than glossy. '
          'No text, no letters, no numbers, no logos, no stickers.'),
    scenes={
        'looking_up': ('Looking up',
                       'Seen from the ground looking up: the person stares down into the camera against a pale '
                       'hazy sky. ' + NO_FIRE),
        'lowrider': ('Lowrider',
                     'The person stands beside a classic lowrider in deep candy paint with gold spoke wheels on a '
                     'wide palm-lined boulevard at a hazy sunset; the car is raised on its hydraulics. The car '
                     'has no badges or logos. ' + NO_FIRE),
        'alley': ('Alley',
                  'The person stands in a sun-bleached alley with a chain-link fence, power lines and plain walls '
                  'with no writing on them. ' + NO_FIRE),
        'corner_store': ('Corner store',
                         'The person stands in front of a small corner store with barred windows and painted '
                         'shapes but no readable words, in late-afternoon sun. ' + NO_FIRE),
        'gfunk_cartoon': ('G-funk cartoon',
                          'The person stands on a sunny LA street with palm trees, drawn as a cartoon that still '
                          'clearly looks like them. ' + NO_FIRE,
                          'A square early-1990s West Coast rap album cover: a bright, bold cartoon illustration '
                          'with thick black outlines, flat sunny colours and a playful mood. '
                          'No text, no letters, no numbers, no logos, no stickers.'),
        'crew_on_block': ('Crew on the block',
                          'The crew stands together on a sunny street in dark clothes, with a lowrider parked '
                          'behind them. ' + NO_FIRE),
    },
    layout_space=LAYOUT_SPACE,
)

STYLES = {style.key: style for style in [NEW_ORLEANS, MEMPHIS, HOUSTON, COMPTON_LA]}

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


def wardrobe(clothing='gold_silk', jewellery=(), accessories=(), people=1):
    # the clothing, jewellery and accessories sentences of a prompt (a crew dresses alike,
    # as on the old crew covers)
    they = 'They all wear matching' if people > 1 else 'They wear'
    sentences = [f'{they} {CLOTHING[clothing].removeprefix("a ").removeprefix("an ") if people > 1 else CLOTHING[clothing]}.']
    pieces = [JEWELLERY[j] for j in jewellery] + [ACCESSORIES[a] for a in accessories]
    if pieces:
        sentences.append(('They all wear ' if people > 1 else 'They wear ') +
                         (', '.join(pieces[:-1]) + ' and ' + pieces[-1] if len(pieces) > 1 else pieces[0]) + '.')
    if not jewellery:
        sentences.append(('None of them wear any jewellery' if people > 1 else 'They wear no jewellery at all') +
                         ': no chains, rings or watches.')
    return ' '.join(sentences)


ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth']
MAX_CREW = len(ORDINALS)
CREW_SCENES = {'crew_lineup', 'crew_mist', 'crew_on_block'}   # scenes made for crews (offered only for crews)


def person(references):
    # how to use the reference photos: one photo, or the same person from several angles
    if references <= 1:
        intro = 'The person in the reference photo'
    else:
        intro = (f'The {references} reference photos show the same person from different angles (straight on '
                 'and turned to each side); this person')
    return (f'{intro} is the main figure, waist-up, in the centre, facing the viewer with a confident '
            f'expression. {KEEP_LIKENESS}')

def crew(people, per_person):
    # how to use the reference photos of a crew: who is in which photos, all of them in the
    # picture together, each kept like their own photos
    if per_person == 1:
        which = ', '.join(f'photo {i + 1} is the {ORDINALS[i]} person' for i in range(people))
    else:
        which = ', '.join(f'photos {i * per_person + 1} to {(i + 1) * per_person} are the {ORDINALS[i]} person'
                          for i in range(people))
    angles = ' (straight on and turned to each side)' if per_person > 1 else ''
    return (f'The reference photos show {people} different people{angles}, in order: {which}. All {people} '
            'appear together in the picture as a crew, side by side from the waist up, each facing the viewer '
            'with a confident expression. Everything said about "the person" in the scene applies to the whole '
            'crew together. Keep every person\'s face, skin tone, hair, facial hair and features exactly as in '
            'their own photos, so each one is clearly recognisable, and never mix their features up.')

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
                'versace', 'chanel', 'prada', 'nike', 'supreme', 'disney', 'marvel',
                'confederate']                      # (a hate symbol to many: see docs/merch-styles/memphis.md)


def check_user_text(text):
    # what's wrong with words a user wants to add to a prompt (empty list = fine). Real
    # people can't all be listed, so famous names other than these aren't caught here
    problems = []
    if len(text) > MAX_USER_TEXT:
        problems.append(f'too long: keep it under {MAX_USER_TEXT} characters')
    lower = f' {re.sub(r"[^a-z0-9&-]+", " ", text.lower())} '
    found = [name for name in BANNED_NAMES if f' {name} ' in lower]
    if found:
        problems.append(f'not allowed (real artists, labels, brands or banned symbols): {", ".join(found)}')
    return problems

def sentence(text):
    # the user's words as a finished sentence, so they don't run into the next one
    text = text.strip()
    return text + '.' if text and text[-1] not in '.!?' else text

def build_prompt(style, scene, references=1, extras='', clothing=None, jewellery=(), accessories=(),
                 details='', custom_scene='', people=1):
    # the full prompt for one scene of a style, for `references` photos of each of `people`
    # people (more than one is a crew). clothing / jewellery / accessories are keys of
    # CLOTHING, JEWELLERY and ACCESSORIES (with clothing=None the AI chooses, as in the
    # likeness test); extras adds any other sentence. The user's own words: scene=CUSTOM
    # uses custom_scene as the whole scene, and details are added to any scene
    if not 1 <= people <= MAX_CREW:
        raise ValueError(f'a cover can have 1 to {MAX_CREW} people')
    if isinstance(style, str):
        style = STYLES[style]
    base = style.base
    if scene == CUSTOM:
        if not custom_scene.strip():
            raise ValueError('a custom scene needs a description')
        scene_text = sentence(custom_scene)
    elif scene in style.scenes:
        scene_text = style.scenes[scene][1]
        if len(style.scenes[scene]) > 2:            # a scene with its own look
            base = style.scenes[scene][2]
    else:
        raise ValueError(f'unknown scene "{scene}"; use one of {list(style.scenes) + [CUSTOM]}')
    worn = wardrobe(clothing, jewellery, accessories, people) if clothing else ''
    user_words = scene == CUSTOM or details.strip()
    who = person(references) if people == 1 else crew(people, references)
    space = style.layout_space if people == 1 else style.layout_space.replace("the person's head", 'their heads')
    parts = [base, scene_text, who, worn, sentence(details), extras.strip(), space,
             GUARDRAILS if user_words else '']
    return ' '.join(part for part in parts if part)
