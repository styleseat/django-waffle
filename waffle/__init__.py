from decimal import Decimal
import random

import django

from waffle.utils import get_setting


VERSION = (0, 10, 1)
__version__ = '.'.join(map(str, VERSION))


def set_flag(request, flag_name, active=True, session_only=False):
    """Set a flag value on a request object."""
    if not hasattr(request, 'waffles'):
        request.waffles = {}
    request.waffles[flag_name] = [active, session_only]


def flag_is_active(request, flag_name):
    from .models import Flag, get_flag_group_ids, get_flag_user_ids

    try:
        flag = Flag.objects.get(name=flag_name)
    except Flag.DoesNotExist:
        return get_setting('FLAG_DEFAULT')

    if get_setting('OVERRIDE'):
        if flag_name in request.GET:
            return request.GET[flag_name] == '1'

    if flag.everyone:
        return True
    elif flag.everyone is False:
        return False

    if flag.testing:  # Testing mode is on.
        tc = get_setting('TEST_COOKIE') % flag_name
        if tc in request.GET:
            on = request.GET[tc] == '1'
            if not hasattr(request, 'waffle_tests'):
                request.waffle_tests = {}
            request.waffle_tests[flag_name] = on
            return on
        if tc in request.COOKIES:
            return request.COOKIES[tc] == 'True'

    user = request.user

    if flag.authenticated and user.is_authenticated():
        return True

    if flag.staff and user.is_staff:
        return True

    if flag.superusers and user.is_superuser:
        return True

    if flag.languages:
        languages = flag.languages.split(',')
        if (hasattr(request, 'LANGUAGE_CODE') and
                request.LANGUAGE_CODE in languages):
            return True

    flag_user_ids = get_flag_user_ids(flag)
    if user.id in flag_user_ids:
        return True

    flag_group_ids = get_flag_group_ids(flag)
    if len(flag_group_ids) > 0:
        try:
            user_group_ids = set(user.groups.all().values_list('id', flat=True))
        except AttributeError:
            django_version = django.VERSION
            if django_version[0] != 1 or django_version[1] > 5:
                raise
        else:
            if len(user_group_ids & flag_group_ids) > 0:
                return True

    if flag.percent and flag.percent > 0:
        if not hasattr(request, 'waffles'):
            request.waffles = {}
        elif flag_name in request.waffles:
            return request.waffles[flag_name][0]

        cookie = get_setting('COOKIE') % flag_name
        if cookie in request.COOKIES:
            flag_active = (request.COOKIES[cookie] == 'True')
            set_flag(request, flag_name, flag_active, flag.rollout)
            return flag_active

        if Decimal(str(random.uniform(0, 100))) <= flag.percent:
            set_flag(request, flag_name, True, flag.rollout)
            return True
        set_flag(request, flag_name, False, flag.rollout)

    return False


def switch_is_active(switch_name):
    from .models import Switch

    try:
        return Switch.objects.get(name=switch_name).active
    except Switch.DoesNotExist:
        return get_setting('SWITCH_DEFAULT')


def sample_is_active(sample_name):
    from .models import Sample

    try:
        sample = Sample.objects.get(name=sample_name)
    except Sample.DoesNotExist:
        return get_setting('SAMPLE_DEFAULT')
    return Decimal(str(random.uniform(0, 100))) <= sample.percent
