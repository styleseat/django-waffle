import time
try:
    from django.utils import timezone as datetime
except ImportError:
    from datetime import datetime
from datetime import datetime as pydatetime

from django.contrib.auth.models import Group
from django.db import models
from django.db.models.signals import post_save, post_delete, m2m_changed

from waffle.compat import AUTH_USER_MODEL, cache
from waffle.utils import get_setting, keyfmt


class Flag(models.Model):
    """A feature flag.

    Flags are active (or not) on a per-request basis.

    """
    name = models.CharField(max_length=100, unique=True,
                            help_text='The human/computer readable name.')
    everyone = models.NullBooleanField(blank=True, help_text=(
        'Flip this flag on (Yes) or off (No) for everyone, overriding all '
        'other settings. Leave as Unknown to use normally.'))
    percent = models.DecimalField(max_digits=3, decimal_places=1, null=True,
                                  blank=True, help_text=(
        'A number between 0.0 and 99.9 to indicate a percentage of users for '
        'whom this flag will be active.'))
    testing = models.BooleanField(default=False, help_text=(
        'Allow this flag to be set for a session for user testing.'))
    superusers = models.BooleanField(default=True, help_text=(
        'Flag always active for superusers?'))
    staff = models.BooleanField(default=False, help_text=(
        'Flag always active for staff?'))
    authenticated = models.BooleanField(default=False, help_text=(
        'Flag always active for authenticate users?'))
    languages = models.TextField(blank=True, default='', help_text=(
        'Activate this flag for users with one of these languages (comma '
        'separated list)'))
    groups = models.ManyToManyField(Group, blank=True, help_text=(
        'Activate this flag for these user groups.'))
    users = models.ManyToManyField(AUTH_USER_MODEL, blank=True, help_text=(
        'Activate this flag for these users.'))
    rollout = models.BooleanField(default=False, help_text=(
        'Activate roll-out mode?'))
    note = models.TextField(blank=True, help_text=(
        'Note where this Flag is used.'))
    created = models.DateTimeField(default=datetime.now, db_index=True,
        help_text=('Date when this Flag was created.'))
    modified = models.DateTimeField(default=datetime.now, help_text=(
        'Date when this Flag was last modified.'))

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.modified = datetime.now()
        super(Flag, self).save(*args, **kwargs)


class Switch(models.Model):
    """A feature switch.

    Switches are active, or inactive, globally.

    """
    name = models.CharField(max_length=100, unique=True,
                            help_text='The human/computer readable name.')
    active = models.BooleanField(default=False, help_text=(
        'Is this flag active?'))
    note = models.TextField(blank=True, help_text=(
        'Note where this Switch is used.'))
    created = models.DateTimeField(default=datetime.now, db_index=True,
        help_text=('Date when this Switch was created.'))
    modified = models.DateTimeField(default=datetime.now, help_text=(
        'Date when this Switch was last modified.'))

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.modified = datetime.now()
        super(Switch, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Switches'


class Sample(models.Model):
    """A sample is true some percentage of the time, but is not connected
    to users or requests.
    """
    name = models.CharField(max_length=100, unique=True,
                            help_text='The human/computer readable name.')
    percent = models.DecimalField(max_digits=4, decimal_places=1, help_text=(
        'A number between 0.0 and 100.0 to indicate a percentage of the time '
        'this sample will be active.'))
    note = models.TextField(blank=True, help_text=(
        'Note where this Sample is used.'))
    created = models.DateTimeField(default=datetime.now, db_index=True,
        help_text=('Date when this Sample was created.'))
    modified = models.DateTimeField(default=datetime.now, help_text=(
        'Date when this Sample was last modified.'))

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.modified = datetime.now()
        super(Sample, self).save(*args, **kwargs)


def _flag_cache_key(flag, key_name_setting):
    return keyfmt(get_setting(key_name_setting), flag.name)


def _get_flag_idset(flag, key_name_setting, field_name):
    cache_key = _flag_cache_key(flag, key_name_setting)
    entry = cache.get(cache_key)
    flag_mdtime =  flag.modified.replace(microsecond=0)
    if (entry is None or
            pydatetime.fromtimestamp(entry['timestamp']) < flag_mdtime):
        ids = getattr(flag, field_name).all().values_list('id', flat=True)
        entry = {
            'timestamp': int(time.mktime(flag.modified.timetuple())),
            'ids': set(ids),
        }
        cache.set(cache_key, entry)
    return entry['ids']


def get_flag_user_ids(flag):
    return _get_flag_idset(flag, 'FLAG_USER_IDS_CACHE_KEY', 'users')


def get_flag_group_ids(flag):
    return _get_flag_idset(flag, 'FLAG_GROUP_IDS_CACHE_KEY', 'groups')


def uncache_flag(**kwargs):
    flag = kwargs.get('instance')
    keys = [
        _flag_cache_key(flag, s)
        for s in ('FLAG_USER_IDS_CACHE_KEY', 'FLAG_GROUP_IDS_CACHE_KEY')]
    cache.delete_many(keys)

post_save.connect(uncache_flag, sender=Flag, dispatch_uid='save_flag')
post_delete.connect(uncache_flag, sender=Flag, dispatch_uid='delete_flag')
m2m_changed.connect(uncache_flag, sender=Flag.users.through,
                    dispatch_uid='m2m_flag_users')
m2m_changed.connect(uncache_flag, sender=Flag.groups.through,
                    dispatch_uid='m2m_flag_groups')
