from datetime import datetime
from typing import Literal, TypeAlias
from .constants import DATETIME_FORMAT

# Define the CSV output fields for all scrapers
FIELDS: list[str] = [
    # common metadata
    "id", "platform", "platform_type", "url", "content_type",
    "timestamp", "scraper_module",
    # core textual data
    "song_title", "artist", "album", "release_year",
    "genre", "language_variant",
    "text", "raw_text",
    # scrape info
    "scrape_date",
]

# Supported scraping targets
SUPPORTED_PLATFORMS: tuple[str, ...] = (
    "musicatm",
    "sanookmusic",
    "youtube",
    "deezer",
    "spotify",
)

PlatformType: TypeAlias = Literal["lyrics-site", "streaming", "fan-archive"]

# Global scrape date for this run
SCRAPE_DATE = datetime.utcnow().strftime(DATETIME_FORMAT)