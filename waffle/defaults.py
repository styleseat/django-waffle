from __future__ import unicode_literals


COOKIE = 'dwf_%s'
TEST_COOKIE = 'dwft_%s'
SECURE = True
MAX_AGE = 2592000  # 1 month in seconds

CACHE_PREFIX = 'waffle:'
FLAG_CACHE_KEY = 'flag:%s'
FLAG_USER_IDS_CACHE_KEY = 'flag:%s:user_ids'
FLAG_GROUP_IDS_CACHE_KEY = 'flag:%s:group_ids'

FLAG_DEFAULT = False
SAMPLE_DEFAULT = False
SWITCH_DEFAULT = False

OVERRIDE = False
