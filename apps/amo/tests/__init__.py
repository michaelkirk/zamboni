from datetime import datetime, timedelta
import random
import time

from django import forms
from django.conf import settings

import elasticutils
import nose
import test_utils
from redisutils import mock_redis, reset_redis

import amo
import addons.search
from addons.models import Addon
from applications.models import Application, AppVersion
from files.models import File, Platform
from translations.models import Translation
from versions.models import Version, ApplicationsVersions


def formset(*args, **kw):
    """
    Build up a formset-happy POST.

    *args is a sequence of forms going into the formset.
    prefix and initial_count can be set in **kw.
    """
    prefix = kw.pop('prefix', 'form')
    total_count = kw.pop('total_count', len(args))
    initial_count = kw.pop('initial_count', len(args))
    data = {prefix + '-TOTAL_FORMS': total_count,
            prefix + '-INITIAL_FORMS': initial_count}
    for idx, d in enumerate(args):
        data.update(('%s-%s-%s' % (prefix, idx, k), v)
                    for k, v in d.items())
    data.update(kw)
    return data


def initial(form):
    """Gather initial data from the form into a dict."""
    data = {}
    for name, field in form.fields.items():
        if form.is_bound:
            data[name] = form[name].data
        else:
            data[name] = form.initial.get(name, field.initial)
        # The browser sends nothing for an unchecked checkbox.
        if isinstance(field, forms.BooleanField):
            val = field.to_python(data[name])
            if not val:
                del data[name]
    return data


class RedisTest(object):
    """Mixin for when you need to mock redis for testing."""

    def _pre_setup(self):
        super(RedisTest, self)._pre_setup()
        self._redis = mock_redis()
        from addons.utils import FeaturedManager, CreaturedManager
        FeaturedManager.build()
        CreaturedManager.build()

    def _post_teardown(self):
        super(RedisTest, self)._post_teardown()
        reset_redis(self._redis)


test_utils.TestCase.__bases__ = (RedisTest,) + test_utils.TestCase.__bases__


def close_to_now(dt):
    """
    Make sure the datetime is within a minute from `now`.
    """
    dt_ts = time.mktime(dt.timetuple())
    dt_minute_ts = time.mktime((dt + timedelta(minutes=1)).timetuple())
    now_ts = time.mktime(datetime.now().timetuple())

    return now_ts >= dt_ts and now_ts < dt_minute_ts


def assert_no_validation_errors(validation):
    """Assert that the validation (JSON) does not contain a traceback.

    Note that this does not test whether the addon passed
    validation or not.
    """
    if hasattr(validation, 'task_error'):
        # FileUpload object:
        error = validation.task_error
    else:
        # Upload detail - JSON output
        error = validation['error']
    if error:
        print '-' * 70
        print error
        print '-' * 70
        raise AssertionError("Unexpected task error: %s" %
                             error.rstrip().split("\n")[-1])


def addon_factory(version_kw={}, file_kw={}, **kw):
    a = Addon.objects.create(type=amo.ADDON_EXTENSION)
    a.status = amo.STATUS_PUBLIC
    a.name = name = 'Addon %s' % a.id
    a.slug = name.replace(' ', '-').lower()
    a.bayesian_rating = random.uniform(1, 5)
    a.average_daily_users = random.randint(200, 2000)
    a.weekly_downloads = random.randint(200, 2000)
    a.created = a.last_updated = datetime(2011, 6, 6, random.randint(0, 23),
                                          random.randint(0, 59))
    version_factory(file_kw, addon=a, **version_kw)
    a.update_version()
    a.status = amo.STATUS_PUBLIC
    for key, value in kw.items():
        setattr(a, key, value)
    a.save()
    return a


def version_factory(file_kw={}, **kw):
    v = Version.objects.create(version='%.1f' % random.uniform(0, 2),
                               **kw)
    a, _ = Application.objects.get_or_create(id=amo.FIREFOX.id)
    av_min, _ = AppVersion.objects.get_or_create(application=a, version='4.0')
    av_max, _ = AppVersion.objects.get_or_create(application=a, version='5.0')
    ApplicationsVersions.objects.create(application=a, version=v,
                                        min=av_min, max=av_max)
    file_factory(version=v, **file_kw)
    return v


def file_factory(**kw):
    v = kw['version']
    p, _ = Platform.objects.get_or_create(id=amo.PLATFORM_ALL.id)
    f = File.objects.create(filename='%s-%s' % (v.addon_id, v.id),
                            platform=p, status=amo.STATUS_PUBLIC, **kw)
    return f


class ESTestCase(test_utils.TestCase):
    """Base class for tests that require elasticsearch."""
    # ES is slow to set up so this uses class setup/teardown. That happens
    # outside Django transactions so be careful to clean up afterwards.
    es = True
    use_es = None

    @classmethod
    def setUpClass(cls):
        cls.es = elasticutils.get_es()
        settings.USE_ELASTIC = True

        if ESTestCase.use_es is None:
            settings.ES_INDEX = 'test_%s' % settings.ES_INDEX
            try:
                cls.es.cluster_health()
                ESTestCase.use_es = True
            except Exception, e:
                print 'Disabling elasticsearch tests.\n%s' % e
                ESTestCase.use_es = False

        if not ESTestCase.use_es:
            raise nose.SkipTest()

        try:
            cls.es.delete_index(settings.ES_INDEX)
        except Exception, e:
            pass

        super(ESTestCase, cls).setUpClass()
        addons.search.setup_mapping()
        cls.add_addons()
        cls.refresh()

    @classmethod
    def tearDownClass(cls):
        settings.USE_ELASTIC = False
        # Delete everything in reverse-order of the foriegn key dependencies.
        models = (Platform, File, ApplicationsVersions, Version,
                  Translation, Addon, AppVersion, Application)
        for model in models:
            model.objects.all().delete()

    @classmethod
    def refresh(cls):
        cls.es.refresh(settings.ES_INDEX, timesleep=0)

    @classmethod
    def add_addons(cls):
        addon_factory(name='user-disabled', disabled_by_user=True)
        addon_factory(name='admin-disabled', status=amo.STATUS_DISABLED)
        addon_factory(status=amo.STATUS_UNREVIEWED)
        addon_factory()
        addon_factory()
        addon_factory()
