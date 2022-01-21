import os
import re
from dataclasses import dataclass, field

EXTENSIONS = ('.mp3',)
NAME_SEPARATORS = ('feat.', ',', '&')
REDUNDANT_STRINGS = ('extended mix', 'original mix', 'radio mix')


@dataclass
class APIs:
    deezer: str
    doublenegative: str

    def __init__(self, deezer: str, doublenegative: str):
        self.deezer = deezer
        self.doublenegative = doublenegative


@dataclass
class Track:
    """Class for storing a track"""
    name: str
    artist: str = field(repr=False)
    song: str = field(repr=False)
    path: str = field(repr=False)
    abs_path: str = field(repr=False)
    search_query: str = field(repr=False)

    def __init__(self, path: str):
        self.path = path
        self.abs_path = os.path.abspath(path)
        self.genre = os.path.basename(os.path.dirname(self.path.resolve()))

        # Strip any extensions and redundant strings
        self.name = re.sub(f"{'|'.join(EXTENSIONS + REDUNDANT_STRINGS)}", "", os.path.basename(self.path))

        # Remove all parenthesis
        self.artist, self.song = re.sub("[()]", "", self.name).split(' - ')

        for sep in NAME_SEPARATORS:
            self.artist = self.artist.lower().split(sep)[0]

        self.search_query = f'{self.song} {self.artist}'


@dataclass
class DownloadResult:
    """Class for storing a download result"""
    track: Track
    outcome: bool

    def __init__(self, track: Track, outcome: bool):
        self.track = track
        self.outcome = outcome
