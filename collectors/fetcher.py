"""Tải trang một cách lịch sự: tôn trọng robots.txt, giãn cách, dừng khi bị chặn."""
import os
import re
import time
from urllib import robotparser
from urllib.parse import urlparse

import requests

DEFAULT_USER_AGENT = "RentalPulse/0.1 (academic student project)"
BLOCK_STATUSES = {403, 429}
# Dấu hiệu trang thử thách của Cloudflare. Không dùng chữ "captcha" trơn vì trang
# bình thường của site cũng có chữ này trong script.
_CHALLENGE = re.compile(
    r"<title>\s*(just a moment|attention required)|cf-chl-|id=\"challenge-form\"",
    re.IGNORECASE,
)


class FetchError(Exception):
    """Lỗi tải trang nói chung."""


class BlockedError(FetchError):
    """Site chặn mình (403, 429, trang thử thách). Phải dừng, không vượt."""


class RobotsDisallowed(FetchError):
    """robots.txt không cho phép đường dẫn này."""


class PoliteFetcher:
    def __init__(self, user_agent=None, min_delay=10.0, timeout=20.0,
                 session=None, sleep=time.sleep, clock=time.monotonic):
        self.user_agent = user_agent or os.getenv("FETCH_USER_AGENT") or DEFAULT_USER_AGENT
        self.min_delay = min_delay
        self.timeout = timeout
        self.session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._last_request = None
        self._robots = {}

    def _get(self, url):
        """Mọi request đều đi qua đây, nên luôn bị giãn cách."""
        if self._last_request is not None:
            remaining = self.min_delay - (self._clock() - self._last_request)
            if remaining > 0:
                self._sleep(remaining)
        try:
            return self.session.get(
                url, headers={"User-Agent": self.user_agent}, timeout=self.timeout
            )
        finally:
            self._last_request = self._clock()

    @staticmethod
    def _raise_if_blocked(resp, url):
        if resp.status_code in BLOCK_STATUSES:
            raise BlockedError(f"HTTP {resp.status_code} từ {url}: site đang chặn, dừng lại")
        if _CHALLENGE.search(resp.text[:20000]):
            raise BlockedError(f"Trang thử thách (Cloudflare) từ {url}: dừng lại")

    def _allowed(self, url):
        parts = urlparse(url)
        root = f"{parts.scheme}://{parts.netloc}"
        parser = self._robots.get(root)
        if parser is None:
            robots_url = root + "/robots.txt"
            resp = self._get(robots_url)
            self._raise_if_blocked(resp, robots_url)
            parser = robotparser.RobotFileParser()
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
            elif resp.status_code == 404:
                parser.allow_all = True  # không có robots.txt: không bị hạn chế
            else:
                parser.disallow_all = True  # không đọc được: thận trọng, coi như cấm
            self._robots[root] = parser
        return parser.can_fetch(self.user_agent, url)

    def fetch(self, url):
        """Trả về HTML. Ném RobotsDisallowed, BlockedError hoặc FetchError khi không được."""
        if not self._allowed(url):
            raise RobotsDisallowed(f"robots.txt không cho phép {url}")
        resp = self._get(url)
        self._raise_if_blocked(resp, url)
        if resp.status_code != 200:
            raise FetchError(f"HTTP {resp.status_code} từ {url}")
        return resp.text