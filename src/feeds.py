"""Curated list of free football/soccer news RSS feeds, verified to parse with good images.

Order matters: the rotation engine cycles through these top-to-bottom so the
page mixes sources evenly. Add/remove freely — keys are the brand labels shown
on the card.
"""

FOOTBALL_FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/11095",
    "Guardian Football": "https://www.theguardian.com/football/rss",
    "Football London": "https://www.football.london/?service=rss",
    "90min": "https://www.90min.com/posts.rss",
    "Football365": "https://www.football365.com/rss",
    "Independent": "https://www.independent.co.uk/sport/football/rss",
    "Mirror Football": "https://www.mirror.co.uk/sport/football/?service=rss",
}
