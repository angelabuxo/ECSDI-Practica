import logging
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from AgentZon.agents.logging_utils import InternalAccessFilter


class InternalAccessFilterTest(unittest.TestCase):
    def test_filters_internal_comm_requests(self):
        record = logging.LogRecord(
            name="werkzeug",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg='127.0.0.1 - - [02/May/2026 15:05:47] "GET /comm?content=abc HTTP/1.1" 200 -',
            args=(),
            exc_info=None,
        )

        self.assertFalse(InternalAccessFilter().filter(record))

    def test_keeps_regular_browser_requests(self):
        record = logging.LogRecord(
            name="werkzeug",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg='127.0.0.1 - - [02/May/2026 15:05:47] "GET / HTTP/1.1" 200 -',
            args=(),
            exc_info=None,
        )

        self.assertTrue(InternalAccessFilter().filter(record))


if __name__ == "__main__":
    unittest.main()
