"""
API views
"""
from datetime import date, timedelta
import itertools
import json
import random
import urllib

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.template.context import get_standard_processors
from django.utils import translation, encoding

import jingo
from tower import ugettext as _, ugettext_lazy
from caching.base import cached_with

import amo
import api
from api.utils import addon_to_dict
from amo.models import manual_order
from amo.urlresolvers import get_url_prefix
from amo.utils import JSONEncoder
from addons.models import Addon
from search.client import (Client as SearchClient, SearchError,
                           SEARCHABLE_STATUSES)
from search import utils as search_utils

ERROR = 'error'
OUT_OF_DATE = ugettext_lazy(
    u"The API version, {0:.1f}, you are using is not valid.  "
    u"Please upgrade to the current version {1:.1f} API.")

xml_env = jingo.env.overlay()
old_finalize = xml_env.finalize
xml_env.finalize = lambda x: amo.helpers.strip_controls(old_finalize(x))


# Hard limit of 30.  The buffer is to try for locale-specific add-ons.
MAX_LIMIT, BUFFER = 30, 10

# "New" is arbitrarily defined as 10 days old.
NEW_DAYS = 10


def partition(seq, key):
    """Group a sequence based into buckets by key(x)."""
    groups = itertools.groupby(sorted(seq, key=key), key=key)
    return ((k, list(v)) for k, v in groups)


def render_xml(request, template, context={}, **kwargs):
    """Safely renders xml, stripping out nasty control characters."""
    if not jingo._helpers_loaded:
        jingo.load_helpers()

    for processor in get_standard_processors():
        context.update(processor(request))

    template = xml_env.get_template(template)
    return template.render(**context)


def render_xml_response(request, template, context={}, **kwargs):
    if 'mimetype' not in kwargs:
        kwargs['mimetype'] = 'text/xml'
    return HttpResponse(render_xml(request, template, context), **kwargs)


def validate_api_version(version):
    """
    We want to be able to deprecate old versions of the API, therefore we check
    for a minimum API version before continuing.
    """
    if float(version) < api.MIN_VERSION:
        return False

    if float(version) > api.MAX_VERSION:
        return False

    return True


def addon_filter(addons, addon_type, limit, app, platform, version,
                 shuffle=True):
    """
    Filter addons by type, application, app version, and platform.

    Add-ons that support the current locale will be sorted to front of list.
    Shuffling will be applied to the add-ons supporting the locale and the
    others separately.

    Doing this in the database takes too long, so we in code and wrap it in
    generous caching.
    """
    APP = app

    if addon_type.upper() != 'ALL':
        try:
            addon_type = int(addon_type)
            if addon_type:
                addons = [a for a in addons if a.type == addon_type]
        except ValueError:
            # `addon_type` is ALL or a type id.  Otherwise we ignore it.
            pass

    # Take out personas since they don't have versions.
    groups = dict(partition(addons,
                            lambda x: x.type == amo.ADDON_PERSONA))
    personas, addons = groups.get(True, []), groups.get(False, [])

    platform = platform.lower()
    if platform != 'all' and platform in amo.PLATFORM_DICT:
        pid = amo.PLATFORM_DICT[platform]
        f = lambda ps: pid in ps or amo.PLATFORM_ALL in ps
        addons = [a for a in addons
                  if f(a.current_version.supported_platforms)]

    if version is not None:
        v = search_utils.convert_version(version)
        f = lambda app: app.min.version_int <= v <= app.max.version_int
        xs = [(a, a.compatible_apps) for a in addons]
        addons = [a for a, apps in xs if apps.get(APP) and f(apps[APP])]

    # Put personas back in.
    addons.extend(personas)

    # We prefer add-ons that support the current locale.
    lang = translation.get_language()
    partitioner = lambda x: (x.description and
                             (x.description.locale == lang))
    groups = dict(partition(addons, partitioner))
    good, others = groups.get(True, []), groups.get(False, [])

    if shuffle:
        random.shuffle(good)
        random.shuffle(others)

    if len(good) < limit:
        good.extend(others[:limit - len(good)])
    return good[:limit]


class APIView(object):
    """
    Base view class for all API views.
    """

    def __call__(self, request, api_version, *args, **kwargs):

        self.version = float(api_version)
        self.format = request.REQUEST.get('format', 'xml')
        self.mimetype = ('text/xml' if self.format == 'xml'
                         else 'application/json')
        self.request = request
        if not validate_api_version(api_version):
            msg = OUT_OF_DATE.format(self.version, api.CURRENT_VERSION)
            return self.render_msg(msg, ERROR, status=403,
                                   mimetype=self.mimetype)

        return self.process_request(*args, **kwargs)

    def render_msg(self, msg, error_level=None, *args, **kwargs):
        """
        Renders a simple message.
        """

        if self.format == 'xml':
            return render_xml_response(self.request, 'api/message.xml',
                {'error_level': error_level, 'msg': msg}, *args, **kwargs)
        else:
            return HttpResponse(json.dumps({'msg': _(msg)}), *args, **kwargs)

    def render(self, template, context):
        context['api_version'] = self.version
        context['api'] = api

        if self.format == 'xml':
            return render_xml_response(self.request, template, context,
                                       mimetype=self.mimetype)
        else:
            return HttpResponse(self.render_json(context),
                                mimetype=self.mimetype)

    def render_json(self, context):
        return json.dumps({'msg': _('Not implemented yet.')})


class AddonDetailView(APIView):

    def process_request(self, addon_id):
        try:
            addon = Addon.objects.id_or_slug(addon_id).get()
        except Addon.DoesNotExist:
            return self.render_msg('Add-on not found!', ERROR, status=404,
                mimetype=self.mimetype)

        return self.render_addon(addon)

    def render_addon(self, addon):
        return self.render('api/addon_detail.xml', {'addon': addon})


def guid_search(request, api_version, guids):
    if settings.FASTER_GUID_SEARCH:
        return _faster_guid_search(request, api_version, guids)
    guids = [g.strip() for g in guids.split(',')] if guids else []
    results = Addon.objects.filter(guid__in=guids, disabled_by_user=False,
                                   status__in=SEARCHABLE_STATUSES)
    return render_xml_response(request, 'api/search.xml',
        {'results': results, 'total': len(results),
         'api_version': api_version, 'api': api})


def _faster_guid_search(request, api_version, guids):
    def render(addon):
        return render_xml(request, 'api/includes/addon.xml',
                          {'addon': addon, 'api_version': api_version,
                           'api': api})

    guids = [g.strip() for g in guids.split(',')] if guids else []
    results = cache.get_many(guids)
    others = set(guids) - set(results.keys())
    if others:
        addons = Addon.objects.filter(guid__in=others, disabled_by_user=False,
                                      status__in=amo.REVIEWED_STATUSES)
        if addons:
            new = dict((addon.guid, render(addon)) for addon in addons)
            cache.set_many(new)
            results.update(new)
    content = SEARCH_RESULT_XML.format(total=len(results),
                                       results=u'\n'.join(results.values()))
    return HttpResponse(content, content_type='text/xml')


# This is like api/search.xml but with pre-rendered {results} and no jinja.
SEARCH_RESULT_XML = u"""\
<?xml version="1.0" encoding="utf-8" ?>
<searchresults total_results="{total}">
  {results}
</searchresults>"""


class SearchView(APIView):

    def process_request(self, query, addon_type='ALL', limit=10,
                        platform='ALL', version=None):
        """
        This queries sphinx with `query` and serves the results in xml.
        """
        sc = SearchClient()
        limit = min(MAX_LIMIT, int(limit))

        opts = {'app': self.request.APP.id}

        if addon_type.upper() != 'ALL':
            try:
                opts['type'] = int(addon_type)
            except ValueError:
                # `addon_type` is ALL or a type id.  Otherwise we ignore it.
                pass

        if version:
            opts['version'] = version

        if platform.upper() != 'ALL':
            opts['platform'] = platform.lower()

        if self.version < 1.5:
            # By default we show public addons only for api_version < 1.5
            opts['status'] = [amo.STATUS_PUBLIC]

            # Fix doubly encoded query strings
            try:
                query = urllib.unquote(query.encode('ascii'))
            except UnicodeEncodeError:
                # This fails if the string is already UTF-8.
                pass
        try:
            results = sc.query(query, limit=limit, **opts)
        except SearchError:
            return self.render_msg('Could not connect to Sphinx search.',
                                   ERROR, status=503, mimetype=self.mimetype)

        return self.render('api/search.xml',
                           {'results': results, 'total': sc.total_found})


class ListView(APIView):

    def process_request(self, list_type='recommended', addon_type='ALL',
                        limit=10, platform='ALL', version=None):
        """
        Find a list of new or featured add-ons.  Filtering is done in Python
        for cache-friendliness and to avoid heavy queries.
        """
        limit = min(MAX_LIMIT, int(limit))
        APP, platform = self.request.APP, platform.lower()
        qs = Addon.objects.listed(APP)
        shuffle = True

        if list_type in ('by_adu', 'featured'):
            qs = qs.exclude(type=amo.ADDON_PERSONA)

        if list_type == 'newest':
            new = date.today() - timedelta(days=NEW_DAYS)
            addons = (qs.filter(created__gte=new)
                      .order_by('-created'))[:limit + BUFFER]
        elif list_type == 'by_adu':
            addons = qs.order_by('-average_daily_users')[:limit + BUFFER]
            shuffle = False  # By_adu is an ordered list.
        elif list_type == 'hotness':
            # Filter to type=1 so we hit visible_idx. Only extensions have a
            # hotness index right now so this is not incorrect.
            addons = (qs.filter(type=amo.ADDON_EXTENSION)
                      .order_by('-hotness'))[:limit + BUFFER]
            shuffle = False
        else:
            ids = Addon.featured_random(APP, self.request.LANG)
            addons = manual_order(qs, ids[:limit + BUFFER], 'addons.id')
            shuffle = False

        args = (addon_type, limit, APP, platform, version, shuffle)
        f = lambda: self._process(addons, *args)
        return cached_with(addons, f, map(encoding.smart_str, args))

    def _process(self, addons, *args):
        return self.render('api/list.xml',
                           {'addons': addon_filter(addons, *args)})

    def render_json(self, context):
        return json.dumps([addon_to_dict(a) for a in context['addons']],
                          cls=JSONEncoder)


class LanguageView(APIView):

    def process_request(self):
        addons = Addon.objects.filter(status=amo.STATUS_PUBLIC,
                                      type=amo.ADDON_LPAPP,
                                      appsupport__app=self.request.APP.id,
                                      disabled_by_user=False).order_by('pk')
        return self.render('api/list.xml', {'addons': addons,
                                            'show_localepicker': True})


# pylint: disable-msg=W0613
def redirect_view(request, url):
    """
    Redirect all requests that come here to an API call with a view parameter.
    """
    dest = '/api/%.1f/%s' % (api.CURRENT_VERSION,
                             urllib.quote(url.encode('utf-8')))
    dest = get_url_prefix().fix(dest)

    return HttpResponsePermanentRedirect(dest)


def request_token_ready(request, token):
    error = request.GET.get('error', '')
    ctx = {'error': error, 'token': token}
    return jingo.render(request, 'piston/request_token_ready.html', ctx)
