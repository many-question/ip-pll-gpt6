"""Approved compute storage; home paths are read-only historical run locators."""
import re
SSD_PROJECT = '/server_local_ssd/jielu/IP-PLL-GPT6'
REMOTE = SSD_PROJECT + '/simulation/cmos_v14_full'
LEGACY_REMOTE = '/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full'
RUN_DIRECTORY_RE = r'((?:' + '|'.join(re.escape(p) for p in [REMOTE, LEGACY_REMOTE]) + r')/[a-f0-9]{8})'
