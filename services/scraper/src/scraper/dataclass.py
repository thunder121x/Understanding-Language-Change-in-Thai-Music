from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar, Literal, Optional

from .config import FIELDS as CONFIG_FIELDS, SCRAPE_DATE
from .constants import DATETIME_FORMAT
from .utils import date_time_formatter  # expects epoch seconds -> str


Platform = Literal["musicatm", "sanookmusic", "youtube", "deezer", "spotify"]
PlatformType = Literal["lyrics-site", "streaming", "fan-archive"]
ContentType = Literal["lyrics", "metadata", "both"]


@dataclass(slots=True, kw_only=True)
class ThaiMusicRecord:
    """
    One scraped Thai lyric item (CSV-ready).
    All normalization happens in __post_init__ to keep dataclass optimizations.
    """

    # ---- metadata ----
    id: str = ""
    platform: Platform = "musicatm"
    platform_type: PlatformType = "lyrics-site"
    url: str = ""
    content_type: ContentType = "lyrics"
    # Accept int (epoch seconds), str (already formatted), or datetime
    timestamp: str | int | datetime | None = None
    scraper_module: Optional[str] = None

    # ---- song info ----
    song_title: str = ""
    artist: str = ""
    album: Optional[str] = None
    # store as str for CSV compatibility; ensure 4-digit validation in post-init
    release_year: Optional[str] = None
    genre: Optional[str] = None
    language_variant: str = "Thai"

    # ---- text ----
    text: str = ""
    raw_text: str = ""

    # ---- scrape info ----
    scrape_date: str = field(default_factory=lambda: SCRAPE_DATE)

    # immutable, ordered CSV header
    CSV_FIELDS: ClassVar[tuple[str, ...]] = tuple(CONFIG_FIELDS)
    CSV_DATETIME_FORMAT: ClassVar[str] = DATETIME_FORMAT

    def __post_init__(self) -> None:
        # --- normalize timestamp -> str (DATETIME_FORMAT) or ""
        if isinstance(self.timestamp, int):
            self.timestamp = date_time_formatter(self.timestamp)  # uses DATETIME_FORMAT
        elif isinstance(self.timestamp, datetime):
            self.timestamp = self.timestamp.strftime(self.CSV_DATETIME_FORMAT)
        elif isinstance(self.timestamp, str):
            # allow ISO-like strings; leave as-is
            pass
        else:
            self.timestamp = ""

        # --- normalize release_year -> 4-digit string or None
        if self.release_year is not None:
            y = str(self.release_year).strip()
            self.release_year = y if (len(y) == 4 and y.isdigit()) else None

        # --- defensive trimming (keeps memory small and CSV clean)
        for attr in ("id", "platform", "platform_type", "url", "content_type",
                     "song_title", "artist", "language_variant"):
            val = getattr(self, attr)
            if isinstance(val, str):
                setattr(self, attr, val.strip())

        # --- ensure text fields are str (not None) for CSV
        self.text = self.text or ""
        self.raw_text = self.raw_text or ""
        self.scrape_date = self.scrape_date or SCRAPE_DATE

    # Return dict with ONLY configured fields and in ORDER
    def to_dict(self) -> dict:
        return {k: getattr(self, k, "") for k in self.CSV_FIELDS}

    @classmethod
    def get_fields(cls) -> list[str]:
        return list(cls.CSV_FIELDS)