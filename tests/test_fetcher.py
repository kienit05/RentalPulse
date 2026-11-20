import pytest

from collectors.fetcher import (
    BlockedError,
    FetchError,
    PoliteFetcher,
    RobotsDisallowed,
)

ROBOTS_OK = "User-agent: *\nAllow: /\n"
ROBOTS_BLOCK_LIST = "User-agent: *\nDisallow: /cho-thue\n"


class FakeResponse:
    def __init__(self, status=200, text=""):
        self.status_code = status
        self.text = text


class FakeSession:
    """Thay requests.Session: trả kết quả theo từng URL, ghi lại các lần gọi."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        return self.routes[url]


class FakeClock:
    """Đồng hồ giả: sleep không ngủ thật, chỉ cộng thời gian."""

    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def make(routes, min_delay=10.0):
    clock = FakeClock()
    session = FakeSession(routes)
    fetcher = PoliteFetcher(
        min_delay=min_delay, session=session, sleep=clock.sleep, clock=clock.monotonic
    )
    return fetcher, session, clock


PAGE = "https://example.test/cho-thue"
ROBOTS = "https://example.test/robots.txt"


def test_returns_html_when_allowed():
    fetcher, _, _ = make({ROBOTS: FakeResponse(200, ROBOTS_OK), PAGE: FakeResponse(200, "<html>ok</html>")})
    assert fetcher.fetch(PAGE) == "<html>ok</html>"


def test_sends_honest_user_agent():
    fetcher, session, _ = make({ROBOTS: FakeResponse(200, ROBOTS_OK), PAGE: FakeResponse(200, "x")})
    fetcher.fetch(PAGE)
    assert all("RentalPulse" in h["User-Agent"] for _, h in session.calls)


def test_waits_between_requests():
    fetcher, _, clock = make({ROBOTS: FakeResponse(200, ROBOTS_OK), PAGE: FakeResponse(200, "x")})
    fetcher.fetch(PAGE)  # 2 request: robots.txt rồi trang
    assert len(clock.slept) == 1
    assert clock.slept[0] == pytest.approx(10.0)


def test_robots_disallow_stops_before_fetching_the_page():
    fetcher, session, _ = make({ROBOTS: FakeResponse(200, ROBOTS_BLOCK_LIST), PAGE: FakeResponse(200, "x")})
    with pytest.raises(RobotsDisallowed):
        fetcher.fetch(PAGE)
    assert [u for u, _ in session.calls] == [ROBOTS]  # không hề gọi trang


@pytest.mark.parametrize("status", [403, 429])
def test_block_status_raises_blocked_and_does_not_retry(status):
    fetcher, session, _ = make({ROBOTS: FakeResponse(200, ROBOTS_OK), PAGE: FakeResponse(status, "")})
    with pytest.raises(BlockedError):
        fetcher.fetch(PAGE)
    assert [u for u, _ in session.calls].count(PAGE) == 1


def test_cloudflare_challenge_page_is_blocked():
    challenge = "<html><head><title>Just a moment...</title></head></html>"
    fetcher, _, _ = make({ROBOTS: FakeResponse(200, ROBOTS_OK), PAGE: FakeResponse(200, challenge)})
    with pytest.raises(BlockedError):
        fetcher.fetch(PAGE)


def test_normal_page_mentioning_captcha_is_not_blocked():
    page = "<html><title>Cho thuê</title><script>var captcha = 1;</script></html>"
    fetcher, _, _ = make({ROBOTS: FakeResponse(200, ROBOTS_OK), PAGE: FakeResponse(200, page)})
    assert fetcher.fetch(PAGE) == page


def test_missing_robots_means_allowed():
    fetcher, _, _ = make({ROBOTS: FakeResponse(404, ""), PAGE: FakeResponse(200, "x")})
    assert fetcher.fetch(PAGE) == "x"


def test_unreadable_robots_is_treated_as_disallowed():
    fetcher, _, _ = make({ROBOTS: FakeResponse(500, ""), PAGE: FakeResponse(200, "x")})
    with pytest.raises(RobotsDisallowed):
        fetcher.fetch(PAGE)


def test_other_error_status_raises_fetch_error():
    fetcher, _, _ = make({ROBOTS: FakeResponse(200, ROBOTS_OK), PAGE: FakeResponse(500, "")})
    with pytest.raises(FetchError):
        fetcher.fetch(PAGE)


def test_robots_is_fetched_only_once_per_site():
    other = "https://example.test/khac"
    fetcher, session, _ = make({
        ROBOTS: FakeResponse(200, ROBOTS_OK),
        PAGE: FakeResponse(200, "a"),
        other: FakeResponse(200, "b"),
    })
    fetcher.fetch(PAGE)
    fetcher.fetch(other)
    assert [u for u, _ in session.calls].count(ROBOTS) == 1