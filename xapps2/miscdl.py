__all__ = ["MiscDL"]

import json
import re
from typing import Any, Dict, Iterator, List, Optional, Pattern

from aiohttp.client_exceptions import ContentTypeError

from .config import DEVICE
from .nikgappsdl import get_nikgapps


class Sources:
    xda: str = "https://forum.xda-developers.com/"
    # vlc: str = "https://get.videolan.org/vlc-android/"
    fdroid: str = "https://f-droid.org/"
    instander: str = "https://raw.githubusercontent.com/the-dise/the-dise.github.io/master/instander/ota.json"


class MiscDL:
    mixplorer_regex: Pattern

    def __init__(self):
        self.mixplorer_regex = re.compile(
            r"(?<=/)attachments/mixplorer_v(?:[6-9]|\d{2,})-[\d-]+api[\w-]+-apk\.\d+"
        )
        super().__init__()

    async def _get_json(self, url: str) -> Optional[Dict]:
        async with self.http.get(url) as resp:
            if resp.status == 200:
                try:
                    return await resp.json()
                except ContentTypeError:
                    return json.loads(await resp.text())

    async def github(self, repo: str, name: str) -> Optional[str]:
        async for apk in self.iter_release_files(repo):
            if apk.get("name") == name:
                return apk.get("browser_download_url")

    async def fdroid(self, pkg_name: str) -> Optional[str]:
        if resp := await self._get_json(f"{Sources.fdroid}api/v1/packages/{pkg_name}"):
            version = resp.get("suggestedVersionCode")
            return f"{Sources.fdroid}repo/{pkg_name}_{version}.apk"

    async def mixplorer(self, varient: str = "") -> Optional[str]:
        if varient == "silver":
            # TODO
            pass
        async with self.http.get(f"{Sources.xda}showpost.php?p=23109280") as resp:
            assert resp.status == 200
            text = await resp.text()
        if match := self.mixplorer_regex.search(text):
            return f"{Sources.xda}{match.group(0)}"

    async def json_api(self, link: str, args: List[str]) -> Optional[str]:
        if resp := await self._get_json(link):
            while len(args) != 0:
                try:
                    resp = resp[args.pop(0)]
                except (IndexError, KeyError):
                    return
            return resp

    async def instander(self) -> Optional[str]:
        async with self.http.get(Sources.instander) as resp:
            assert resp.status == 200
            text = await resp.text()
            return json.loads(text).get("link")

    async def iter_release_files(self, repo: str) -> Iterator[Any]:
        if resp := (
            await self._get_json(f"https://api.github.com/repos/{repo}/releases/latest")
        ):
            for k in resp.get("assets"):
                yield k

    async def nekox(self, varient: str = "mini") -> Optional[str]:
        return await self.github(
            "NekoX-Dev/NekoX", f"NekoX-{varient}-{DEVICE.arch}-release.apk"
        )

    async def niksgapps(self, varient: str = "basic") -> Optional[str]:
        if DEVICE.arch != "arm64-v8a":
            return
        if link := await get_nikgapps(DEVICE.android_str, varient):
            async with self.http.get(link) as resp:
                assert resp.status == 200
                text = await resp.text()
                if match := re.search(
                    r"<a href=\"(?P<link>\S+)\">direct\slink</a>", text
                ):
                    return match.group("link")
