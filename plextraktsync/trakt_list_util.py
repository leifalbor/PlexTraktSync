from __future__ import annotations

from itertools import count

from plexapi.video import Episode
from trakt.core import get
from trakt.users import UserList

from plextraktsync.factory import logger


class LazyUserList(UserList):
    @get
    def get_items(self):
        data = yield f"lists/{self.trakt}/items"
        for item in data:
            if "type" not in item:
                continue
            item_type = item["type"]
            item_data = item.pop(item_type)
            self._items.append((item_type + "s", item_data["ids"]["trakt"]))
        yield self._items

    @classmethod
    @get
    def _get(cls, title, id):
        data = yield f"lists/{id}"
        ulist = cls(creator=data['user']['username'], **data)
        ulist.get_items()
        yield ulist


class TraktList:
    def __init__(self, listid, listname):
        self.name = listname
        self.plex_items = []
        self.description = None
        if listid is not None:
            userlist = LazyUserList._get(listname, listid)
            self.description = userlist.description
            list_items = userlist._items
            prelist = [
                (elem[0], elem[1])
                for elem in list_items
                if elem[0] in ["movies", "episodes"]
            ]
            self.trakt_items = dict(zip(prelist, count(1)))

    @property
    def plex_items_sorted(self):
        """
        Returns items sorted by trakt rank

        https://github.com/Taxel/PlexTraktSync/pull/58
        """
        if len(self.plex_items) == 0:
            return []

        _, items = zip(*sorted(dict(reversed(self.plex_items)).items()))
        return items

    @staticmethod
    def from_trakt_list(listname, trakt_list):
        tl = TraktList(None, listname)
        tl.trakt_items = dict(
            zip([(elem.media_type, elem.trakt) for elem in trakt_list], count(1))
        )
        return tl

    def addPlexItem(self, trakt_item, plex_item):
        rank = self.trakt_items.get((trakt_item.media_type, trakt_item.trakt))
        if rank is not None:
            self.plex_items.append((rank, plex_item))
            if isinstance(plex_item, Episode):
                logger.info(
                    f"Added to list '{self.name}': {plex_item.show()}: {plex_item.seasonEpisode}"
                )
            else:
                logger.info(f"Added to list '{self.name}': {plex_item}")
