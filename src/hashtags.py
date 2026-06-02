"""100 football/soccer hashtags, used 5 per post in rotating blocks.

Post 1 -> tags 1-5, post 2 -> 6-10, ... post 20 -> 96-100, then it wraps.
`#thecrossbar` is added to every post on top of the rotating 5 (see main.py).
"""

BRAND_TAG = "thecrossbar"           # always included, on top of the rotating 5
PER_POST = 5

HASHTAGS = [
    # core football (1-20)
    "football", "soccer", "footballnews", "soccernews", "footballfans",
    "thebeautifulgame", "footy", "footballlife", "footballworld", "footballupdate",
    "matchday", "goals", "goal", "footballhighlights", "footballdaily",
    "footballtwitter", "footballcommunity", "footballlovers", "footballgram", "footballclub",
    # competitions / leagues (21-40)
    "premierleague", "epl", "championsleague", "uefa", "laliga",
    "seriea", "bundesliga", "ligue1", "europaleague", "worldcup",
    "fifa", "euros", "facup", "carabaocup", "copadelrey",
    "mls", "saudipro", "internationalbreak", "wsl", "uefachampionsleague",
    # big clubs (41-60)
    "manchesterunited", "mancity", "liverpool", "arsenal", "chelsea",
    "tottenham", "realmadrid", "barcelona", "bayernmunich", "juventus",
    "psg", "acmilan", "intermilan", "atleticomadrid", "borussiadortmund",
    "newcastleunited", "astonvilla", "westham", "everton", "napoli",
    # players / transfers (61-78)
    "messi", "ronaldo", "cr7", "mbappe", "haaland",
    "vinejr", "bellingham", "saka", "transfer", "transfernews",
    "transferwindow", "deadlineday", "signing", "loan", "freeagent",
    "goldenboot", "ballondor", "goat",
    # match / fan culture (79-92)
    "derby", "elclasico", "northwestderby", "northlondonderby", "kickoff",
    "fulltime", "stoppagetime", "penalty", "freekick", "hattrick",
    "cleansheet", "assist", "comeback", "extratime",
    # engagement (93-100)
    "footballfever", "matchnight", "gameweek", "topfootball", "trendingfootball",
    "footballfamily", "viralfootball", "footballforever",
]

assert len(HASHTAGS) == 100, f"expected 100 hashtags, got {len(HASHTAGS)}"


def block_at(cursor: int) -> list[str]:
    """Return the 5 hashtags starting at `cursor` (wrapping around the 100)."""
    n = len(HASHTAGS)
    c = cursor % n
    return [HASHTAGS[(c + i) % n] for i in range(PER_POST)]


def render(cursor: int) -> str:
    """'#thecrossbar #tag1 #tag2 #tag3 #tag4 #tag5' for the given block."""
    tags = [BRAND_TAG] + block_at(cursor)
    return " ".join(f"#{t}" for t in tags)
