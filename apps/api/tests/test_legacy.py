# -*- coding: utf8 -*-
from datetime import datetime, timedelta
import json
import os
from textwrap import dedent

from django.core.cache import cache
from django.conf import settings
from django.test.client import Client

import jingo
from mock import patch
from nose.tools import eq_
from pyquery import PyQuery as pq

import amo
import api
import api.utils
from amo import helpers
from amo.tests import TestCase
from amo.urlresolvers import reverse
from addons.cron import reset_featured_addons
from addons.models import (Addon, AppSupport, Feature, Preview)
from addons.utils import FeaturedManager
from applications.models import Application
from bandwagon.models import Collection, CollectionAddon, FeaturedCollection
from files.tests.test_models import UploadTest
from search.tests import SphinxTestCase
from search.utils import stop_sphinx


def api_url(x, app='firefox', lang='en-US', version=1.2):
    return '/%s/%s/api/%.1f/%s' % (lang, app, version, x)

client = Client()
make_call = lambda *args, **kwargs: client.get(api_url(*args, **kwargs))


def test_json_not_implemented():
    eq_(api.views.APIView().render_json({}), '{"msg": "Not implemented yet."}')


class UtilsTest(TestCase):
    fixtures = ['base/addon_3615']

    def setUp(self):
        self.a = Addon.objects.get(pk=3615)

    def test_dict(self):
        """Verify that we're getting dict."""
        d = api.utils.addon_to_dict(self.a)
        assert d, 'Add-on dictionary not found'
        assert d['learnmore'].endswith('/addon/a3615/?src=api'), (
            'Add-on details URL does not end with "?src=api"')

    def test_dict_disco(self):
        """Check for correct add-on detail URL for discovery pane."""
        d = api.utils.addon_to_dict(self.a, disco=True,
                                    src='discovery-personalrec')
        u = '%s%s?src=discovery-personalrec' % (settings.SERVICES_URL,
            reverse('discovery.addons.detail', args=['a3615']))
        eq_(d['learnmore'], u)

    def test_sanitize(self):
        """Check that tags are stripped for summary and description."""
        self.a.summary = self.a.description = 'i <3 <a href="">amo</a>!'
        self.a.save()
        d = api.utils.addon_to_dict(self.a)
        eq_(d['summary'], 'i &lt;3 amo!')
        eq_(d['description'], 'i &lt;3 amo!')


class No500ErrorsTest(TestCase):
    """
    A series of unfortunate urls that have caused 500 errors in the past.
    """
    def test_search_bad_type(self):
        """
        For search/:term/:addon_type <-- addon_type should be an integer.
        """
        response = make_call('/search/foo/theme')
        # We'll likely get a 503 since Sphinx is off and that
        # is good.  We just don't want 500 errors.
        assert response.status_code != 500, "We received a 500 error, wtf?"

    def test_list_bad_type(self):
        """
        For list/new/:addon_type <-- addon_type should be an integer.
        """
        response = make_call('/list/new/extension')
        assert response.status_code != 500, "We received a 500 error, wtf?"

    def test_utf_redirect(self):
        """Test that urls with unicode redirect properly."""
        response = make_call(u'search/ツールバー', version=1.5)
        assert response.status_code != 500, "Unicode failed to redirect."

    def test_manual_utf_search(self):
        """If someone searches for non doubly encoded data using an old API we
        should not try to decode it."""
        response = make_call(u'search/für', version=1.2)
        assert response.status_code != 500, "ZOMG Unicode fails."

    def test_broken_guid(self):
        response = make_call(u'search/guid:+972"e4c6-}', version=1.5)
        assert response.status_code != 500, "Failed to cope with guid"


class ControlCharacterTest(TestCase):
    """This test is to assure we aren't showing control characters."""

    fixtures = ('base/addon_3615',)

    def test(self):
        a = Addon.objects.get(pk=3615)
        a.name = "I ove You"
        a.save()
        response = make_call('addon/3615')
        self.assertNotContains(response, '')


class StripHTMLTest(TestCase):
    fixtures = ('base/addon_3615',)

    def test(self):
        """For API < 1.5 we remove HTML."""
        a = Addon.objects.get(pk=3615)
        a.eula = '<i>free</i> stock tips'
        a.summary = '<i>xxx video</i>s'
        a.description = 'FFFF<b>UUUU</b>'
        a.save()
        r = make_call('addon/3615', version=1.5)
        doc = pq(r.content)
        eq_(doc('eula').html(), '<i>free</i> stock tips')
        eq_(doc('summary').html(), '&lt;i&gt;xxx video&lt;/i&gt;s')
        eq_(doc('description').html(), 'FFFF<b>UUUU</b>')
        r = make_call('addon/3615')
        doc = pq(r.content)
        eq_(doc('eula').html(), 'free stock tips')
        eq_(doc('summary').html(), 'xxx videos')
        eq_(doc('description').html(), 'FFFFUUUU')


class APITest(TestCase):
    fixtures = ['base/apps', 'base/addon_3615', 'base/addon_4664_twitterbar',
                'base/addon_5299_gcal', 'perf/index']

    def setUp(self):
        patcher = patch.object(settings, 'NEW_FEATURES', False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_api_caching(self):
        response = self.client.get('/en-US/firefox/api/1.5/addon/3615')
        eq_(response.status_code, 200)
        self.assertContains(response, '<author id="')

        # Make sure we don't cache the 1.5 response for 1.2.
        response = self.client.get('/en-US/firefox/api/1.2/addon/3615')
        eq_(response.status_code, 200)
        self.assertContains(response, '<author>')

    def test_redirection(self):
        """
        Test that /api/addon is redirected to /api/LATEST_API_VERSION/addon
        """
        response = self.client.get('/en-US/firefox/api/addon/12', follow=True)
        last_link = response.redirect_chain[-1]
        assert last_link[0].endswith('en-US/firefox/api/%.1f/addon/12' %
            api.CURRENT_VERSION)

    def test_forbidden_api(self):
        """
        APIs older than api.MIN_VERSION are deprecated, and we send a 403.
        We suggest people to use api.CURRENT_VERSION.
        """

        response = self.client.get('/en-US/firefox/api/0.9/addon/12')
        self.assertContains(response, 'The API version, %.1f, you are using '
            'is not valid. Please upgrade to the current version %.1f '
            'API.' % (0.9, api.CURRENT_VERSION), status_code=403)

    def test_addon_detail_missing(self):
        """
        Check missing addons.
        """
        response = self.client.get('/en-US/firefox/api/%.1f/addon/999' %
            api.CURRENT_VERSION)

        self.assertContains(response, 'Add-on not found!', status_code=404)

    def test_addon_detail_appid(self):
        """
        Make sure we serve an appid.  See
        https://bugzilla.mozilla.org/show_bug.cgi?id=546542.
        """
        response = self.client.get('/en-US/firefox/api/%.1f/addon/3615' %
                                   api.CURRENT_VERSION)
        self.assertContains(response,
                '<appID>{ec8030f7-c20a-464f-9b0e-13a3a9e97384}</appID>')

    def test_addon_detail_empty_eula(self):
        """
        Empty EULA should show up as '' not None.  See
        https://bugzilla.mozilla.org/show_bug.cgi?id=546542.
        """
        response = self.client.get('/en-US/firefox/api/%.1f/addon/4664' %
                                   api.CURRENT_VERSION)
        self.assertContains(response, '<eula></eula>')

    def test_addon_detail_rating(self):
        a = Addon.objects.get(pk=4664)
        response = self.client.get('/en-US/firefox/api/%.1f/addon/4664' %
                                   api.CURRENT_VERSION)
        self.assertContains(response, '<rating>%d</rating>' %
                            int(round(a.average_rating)))

    def test_addon_detail(self):
        """
        Test for expected strings in the XML.
        """
        response = self.client.get('/en-US/firefox/api/%.1f/addon/3615' % 1.2)

        self.assertContains(response, "<name>Delicious Bookmarks</name>")
        self.assertContains(response, """id="1">Extension</type>""")
        self.assertContains(response,
                """<guid>{2fa4ed95-0317-4c6a-a74c-5f3e3912c1f9}</guid>""")
        self.assertContains(response, "<version>2.1.072</version>")
        self.assertContains(response, '<status id="4">Fully Reviewed</status>')
        self.assertContains(response,
            u'<author>55021 \u0627\u0644\u062a\u0637\u0628</author>')
        self.assertContains(response, "<summary>Delicious Bookmarks is the")
        self.assertContains(response, "<description>This extension integrates")

        icon_url = settings.ADDON_ICON_URL % (3615, 32, '')
        self.assertContains(response, "<icon>" + icon_url)
        self.assertContains(response, "<application>")
        self.assertContains(response, "<name>Firefox</name>")
        self.assertContains(response, "<application_id>1</application_id>")
        self.assertContains(response, "<min_version>2.0</min_version>")
        self.assertContains(response, "<max_version>3.7a1pre</max_version>")
        self.assertContains(response, "<os>ALL</os>")
        self.assertContains(response, "<eula>")
        self.assertContains(response, "/icons/no-preview.png</thumbnail>")
        self.assertContains(response, "<rating>3</rating>")
        self.assertContains(response,
                "/en-US/firefox/addon/a3615/?src=api</learnmore>")
        self.assertContains(response,
                """hash="sha256:3808b13ef8341378b9c8305ca64820095"""
                '4ee7dcd8dce09fef55f2673458bc31f"')

    def test_whitespace(self):
        """Whitespace is apparently evil for learnmore and install."""
        r = make_call('addon/3615')
        doc = pq(r.content)
        learnmore = doc('learnmore')[0].text
        eq_(learnmore, learnmore.strip())

        install = doc('install')[0].text
        eq_(install, install.strip())

    def test_double_site_url(self):
        """
        For some reason I noticed hostnames getting doubled up.  This checks
        that it doesn't happen.
        """
        response = make_call('addon/4664', version=1.5)
        self.assertNotContains(response, settings.SITE_URL + settings.SITE_URL)

    def test_absolute_install_url(self):
        response = make_call('addon/4664', version=1.2)
        doc = pq(response.content)
        url = doc('install').text()
        expected = '%s/firefox/downloads/file' % settings.SITE_URL
        assert url.startswith(expected), url

    def test_15_addon_detail(self):
        """
        For an api>1.5 we need to verify we have:
        # Contributions information, including a link to contribute, suggested
          amount, and Meet the Developers page
        # Number of user reviews and link to view them
        # Total downloads, weekly downloads, and latest daily user counts
        # Add-on creation date
        # Link to the developer's profile
        # File size
        """
        e = jingo.env.filters['e']

        def urlparams(x, *args, **kwargs):
            return e(helpers.urlparams(x, *args, **kwargs))

        needles = (
                '<addon id="4664">',
                "<contribution_data>",
                "%s/en-US/firefox/addon/4664/contribute/?src=api</link>"
                    % settings.SITE_URL,
                "<meet_developers>",
                "%s/en-US/firefox/addon/4664/developers?src=api"
                    % settings.SITE_URL,
                "</meet_developers>",
                """<reviews num="131">""",
                "%s/en-US/firefox/addon/4664/reviews/?src=api"
                    % settings.SITE_URL,
                "<total_downloads>1352192</total_downloads>",
                "<weekly_downloads>13849</weekly_downloads>",
                "<daily_users>67075</daily_users>",
                '<author id="2519"',
                "%s/en-US/firefox/user/2519/?src=api</link>"
                    % settings.SITE_URL,
                "<previews>",
                """<preview position="0">""",
                "<caption>"
                    "TwitterBar places an icon in the address bar.</caption>",
                """<full type="image/png">""",
                urlparams(settings.PREVIEW_FULL_URL %
                          ('20', 20397, 1209834208), src='api'),
                """<thumbnail type="image/png">""",
                urlparams(settings.PREVIEW_THUMBNAIL_URL %
                          ('20', 20397, 1209834208), src='api'),
                "<developer_comments>Embrace hug love hug meow meow"
                    "</developer_comments>",
                'size="100352"',
                '<homepage>http://www.chrisfinke.com/addons/twitterbar/'
                    '</homepage>',
                '<support>http://www.chrisfinke.com/addons/twitterbar/'
                    '</support>',
                )

        response = make_call('addon/4664', version=1.5)
        doc = pq(response.content)

        tags = {
                'suggested_amount': (
                    {'currency': 'USD', 'amount': '5.00'}, '$5.00'),
                'created': ({'epoch': '1174134235'}, '2007-03-17T12:23:55Z'),
                'last_updated': (
                    {'epoch': '1272326983'}, '2010-04-27T00:09:43Z'),
                }

        for tag, v in tags.items():
            attrs, text = v
            el = doc(tag)
            for attr, val in attrs.items():
                eq_(el.attr(attr), val)

            eq_(el.text(), text)

        for needle in needles:
            self.assertContains(response, needle)

    def test_no_suggested_amount(self):
        Addon.objects.filter(id=4664).update(suggested_amount=None)
        response = make_call('addon/4664', version=1.5)
        assert '<suggested_amount' not in response.content

    def test_beta_channel(self):
        """
        This tests that addons with files in beta will have those files
        displayed.
        """
        response = make_call('addon/5299', version=1.5)

        needles = (
            """<install hash="sha256:4395f9cf4934ecc8f22d367c2a301fd7""",
            """9613b68937c59e676e92e4f0a89a5b92" """,
            'size="24576"',
            'status="Beta">',
            "/downloads/file/64874/better_gcal-0.4-fx.xpi?src=api",
        )

        for needle in needles:
            self.assertContains(response, needle)

    def test_sphinx_off(self):
        """
        This tests that if sphinx is turned off that you will get an error.
        """
        # Shut down sphinx if it's configured.
        if settings.SPHINX_SEARCHD and settings.SPHINX_INDEXER:
            stop_sphinx()

        os.environ['DJANGO_ENVIRONMENT'] = 'test'
        response = self.client.get("/en-US/firefox/api/1.2/search/foo")
        self.assertContains(response, "Could not connect to Sphinx search.",
                            status_code=503)
    test_sphinx_off.sphinx = True

    def test_slug(self):
        self.assertContains(make_call('addon/5299', version=1.5),
                            '<slug>%s</slug>' %
                            Addon.objects.get(pk=5299).slug)

    @patch.object(settings, 'NEW_FEATURES', False)
    def test_is_featured(self):
        self.assertContains(make_call('addon/5299', version=1.5),
                            '<featured>0</featured>')
        Feature.objects.create(addon_id=5299,
                               start=datetime.now() - timedelta(days=10),
                               end=datetime.now() + timedelta(days=10),
                               application_id=amo.FIREFOX.id,
                               locale='ja')
        reset_featured_addons()
        for lang, app, result in [('ja', 'firefox', 1),
                                  ('en-US', 'firefox', 0),
                                  ('ja', 'seamonkey', 0)]:
            self.assertContains(make_call('addon/5299', version=1.5,
                                          lang=lang, app=app),
                                '<featured>%s</featured>' % result)

    @patch.object(settings, 'NEW_FEATURES', True)
    def test_new_is_featured(self):
        self.assertContains(make_call('addon/5299', version=1.5),
                            '<featured>0</featured>')
        c = CollectionAddon.objects.create(
                addon=Addon.objects.get(id=5299),
                collection=Collection.objects.create())
        FeaturedCollection.objects.create(locale='ja',
            application=Application.objects.get(id=amo.FIREFOX.id),
            collection=c.collection)
        FeaturedManager.redis().kv.clear()
        reset_featured_addons()
        for lang, app, result in [('ja', 'firefox', 1),
                                  ('en-US', 'firefox', 0),
                                  ('ja', 'seamonkey', 0)]:
            self.assertContains(make_call('addon/5299', version=1.5,
                                          lang=lang, app=app),
                                '<featured>%s</featured>' % result)

    def test_default_icon(self):
        addon = Addon.objects.get(pk=5299)
        addon.update(icon_type='')
        self.assertContains(make_call('addon/5299'), '<icon></icon>')

    def test_thumbnail_size(self):
        addon = Addon.objects.get(pk=5299)
        preview = Preview.objects.create(addon=addon)
        preview.sizes = {'thumbnail': [200, 150]}
        preview.save()
        result = make_call('addon/5299', version=1.5)
        self.assertContains(result, '<full type="">')
        self.assertContains(result,
                            '<thumbnail type="" width="200" height="150">')

    def test_performance_data(self):
        with self.assertNumQueries(20):
            response = self.client.get('/en-US/firefox/api/%.1f/addon/3615' %
                                       api.CURRENT_VERSION)
        doc = pq(response.content)
        eq_(doc('performance application').eq(0).attr('name'), 'fx')
        eq_(doc('performance application').eq(0).attr('version'), '3.6')
        eq_(doc('performance application platform').eq(0).attr('name'), 'mac')
        eq_(doc('performance application platform').eq(0).attr('version'),
            '10.6')
        result = doc('performance application platform result').eq(0)
        eq_(result.attr('type'), 'ts')
        eq_(result.attr('average'), '5.21')
        eq_(result.attr('baseline'), '1.2')

    @patch.object(settings, 'PERF_THRESHOLD', 335)
    def test_performance_threshold_false(self):
        response = self.client.get('/en-US/firefox/api/%.1f/addon/3615' %
                                   api.CURRENT_VERSION)
        doc = pq(response.content)
        result = doc('performance application platform result').eq(0)
        eq_(result.attr('above_threshold'), 'false')

    @patch.object(settings, 'PERF_THRESHOLD', 332)
    def test_performance_threshold_true(self):
        response = self.client.get('/en-US/firefox/api/%.1f/addon/3615' %
                                   api.CURRENT_VERSION)
        doc = pq(response.content)
        result = doc('performance application platform result').eq(0)
        eq_(result.attr('above_threshold'), 'true')


class ListTest(TestCase):
    """Tests the list view with various urls."""
    fixtures = ['base/apps', 'base/addon_3615', 'base/featured']

    def setUp(self):
        # TODO(cvan): Remove this once featured collections are enabled.
        patcher = patch.object(settings, 'NEW_FEATURES', False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_defaults(self):
        """
        This tests the default settings for /list.
        i.e. We should get 3 items by default.
        """
        response = make_call('list')
        self.assertContains(response, '<addon id', 3)

    def test_randomness(self):
        """
        This tests that we're sufficiently random when recommending addons.

        We can test for this by querying /list/recommended a number of times
        until we get two response.contents that do not match.
        """
        response = make_call('list/recommended')
        all_identical = True

        for i in range(99):
            cache.clear()
            current_request = make_call('list/recommended')
            if current_request.content != response.content:
                all_identical = False
                break

        assert not all_identical, (
                "All 100 requests returned the exact same response.")

    def test_type_filter(self):
        """
        This tests that list filtering works.
        E.g. /list/recommended/theme gets only shows themes
        """
        response = make_call('list/recommended/9/1')
        self.assertContains(response, """<type id="9">Persona</type>""", 1)

    def test_persona_search_15(self):
        response = make_call('list/recommended/9/1', version=1.5)
        self.assertContains(response, """<type id="9">Persona</type>""", 1)

    def test_limits(self):
        """
        Assert /list/recommended/all/1 gets one item only.
        """
        response = make_call('list/recommended/all/1')
        self.assertContains(response, "<addon id", 1)

    def test_version_filter(self):
        """
        Assert that filtering by application version works.

        E.g.
        /list/new/all/1/mac/4.0 gives us nothing
        """
        response = make_call('list/new/1/1/all/4.0')
        self.assertNotContains(response, "<addon id")

    def test_backfill(self):
        """
        The /list/recommended should first populate itself with addons in its
        locale.  If it doesn't reach the desired limit, it should backfill from
        the general population of featured addons.
        """
        response = make_call('list', lang='fr')
        self.assertContains(response, "<addon id", 3)

        response = make_call('list', lang='he')
        self.assertContains(response, "<addon id", 3)

    def test_browser_featured_list(self):
        """
        This is a query that a browser would use to show it's featured list.

        c.f.: https://bugzilla.mozilla.org/show_bug.cgi?id=548114
        """
        response = make_call('list/featured/all/10/Linux/3.7a2pre',
                            version=1.3)
        self.assertContains(response, "<addons>")

    def test_average_daily_users(self):
        """Verify that average daily users returns data in order."""
        r = make_call('list/by_adu', version=1.5)
        doc = pq(r.content)
        vals = [int(a.text) for a in doc("average_daily_users")]
        sorted_vals = sorted(vals, reverse=True)
        eq_(vals, sorted_vals)

    def test_adu_no_personas(self):
        """Verify that average daily users does not return Persona add-ons."""
        response = make_call('list/by_adu')
        self.assertNotContains(response, """<type id="9">Persona</type>""")

    def test_featured_no_personas(self):
        """Verify that featured does not return Persona add-ons."""
        response = make_call('list/featured')
        self.assertNotContains(response, """<type id="9">Persona</type>""")

    def test_json(self):
        """Verify that we get some json."""
        r = make_call('list/by_adu?format=json', version=1.5)
        assert json.loads(r.content)

    def test_unicode(self):
        make_call(u'list/featured/all/10/Linux/3.7a2prexec\xb6\u0153\xec\xb2')


class NewListTest(ListTest):
    """Tests the list view with various urls."""
    fixtures = ListTest.fixtures + ['addons/featured',
                                    'bandwagon/featured_collections',
                                    'base/collections']

    def setUp(self):
        # TODO(cvan): Remove this once featured collections are enabled.
        patcher = patch.object(settings, 'NEW_FEATURES', True)
        patcher.start()
        self.addCleanup(patcher.stop)


class SeamonkeyFeaturedTest(TestCase):
    fixtures = ['base/seamonkey']

    def test_seamonkey_wankery(self):
        """
        An add-on used to support seamonkey, but not in its current_version.
        This was making our filters crash.
        """
        response = make_call('/list/featured/all/10/all/1', app='seamonkey')
        eq_(response.context['addons'], [])


class TestGuidSearch(TestCase):
    fixtures = ('base/apps', 'base/addon_6113', 'base/addon_3615')

    def test_success(self):
        guids = ['{22870005-adef-4c9d-ae36-d0e1f2f27e5a}',
                 '{2fa4ed95-0317-4c6a-a74c-5f3e3912c1f9}']
        r = make_call('search/guid:' + ','.join(guids))
        eq_(set(['3615', '6113']),
            set([a.attrib['id'] for a in pq(r.content)('addon')]))

        # Now add a new addon and make sure it's inside the results.
        new = Addon.objects.create(type=amo.ADDON_EXTENSION, guid='woohoo',
                                   name=u'\xd8\u1124 UNICODE')
        new.update(status=amo.STATUS_PUBLIC)
        guids.append(new.guid)
        r = make_call('search/guid:' + ','.join(guids))
        eq_(set(['3615', '6113', str(new.id)]),
            set([a.attrib['id'] for a in pq(r.content)('addon')]))

    def test_block_inactive(self):
        Addon.objects.filter(id=6113).update(disabled_by_user=True)
        r = make_call('search/guid:{22870005-adef-4c9d-ae36-d0e1f2f27e5a},'
                      '{2fa4ed95-0317-4c6a-a74c-5f3e3912c1f9}')
        eq_(set(['3615']),
            set([a.attrib['id'] for a in pq(r.content)('addon')]))

    def test_block_nonpublic(self):
        Addon.objects.filter(id=6113).update(status=amo.STATUS_UNREVIEWED)
        r = make_call('search/guid:{22870005-adef-4c9d-ae36-d0e1f2f27e5a},'
                      '{2fa4ed95-0317-4c6a-a74c-5f3e3912c1f9}')
        eq_(set(['3615']),
            set([a.attrib['id'] for a in pq(r.content)('addon')]))

    def test_empty(self):
        # Bug: https://bugzilla.mozilla.org/show_bug.cgi?id=607044
        # guid:foo, should search for just 'foo' and not empty guids.
        r = make_call('search/guid:koberger,')
        doc = pq(r.content)
        # No addons should exist with guid koberger and the , should not
        # indicate that we are searching for null guid.
        eq_(len(doc('addon')), 0)


class SearchTest(SphinxTestCase):
    fixtures = ('base/apps', 'base/addon_6113', 'base/addon_40',
                'base/addon_3615', 'base/addon_6704_grapple',
                'base/addon_4664_twitterbar', 'base/addon_10423_youtubesearch')

    no_results = """<searchresults total_results="0">"""

    def test_double_escaping(self):
        """
        For API < 1.5 we use double escaping in search.
        """
        resp = make_call('search/%25E6%2596%25B0%25E5%2590%258C%25E6%2596%'
                '2587%25E5%25A0%2582/all/10/WINNT/3.6', version=1.2)
        self.assertContains(resp, '<addon id="6113">')

    def test_zero_results(self):
        """
        Tests that the search API correctly gives us zero results found.
        """
        # The following URLs should yield zero results.
        zeros = (
                 "/en-US/sunbird/api/1.2/search/yslow",
                 "yslow category:alerts",
                 "jsonview version:1.0",
                 "firebug type:dictionary",
                 "grapple platform:linux",
                 "firebug/3",
                 "grapple/all/10/Linux",
                 "jsonview/all/10/Darwin/1.0",)

        for url in zeros:
            if not url.startswith('/'):
                url = '/en-US/firefox/api/1.2/search/' + url

            response = self.client.get(url)
            self.assertContains(response, self.no_results, msg_prefix=url)

    def test_search_for_specifics(self):
        """
        Tests that the search API correctly returns specific results.
        """
        expect = {
                  'delicious': 'Delicious Bookmarks',
                  'delicious category:feeds': 'Delicious Bookmarks',
                  'delicious version:3.6': 'Delicious Bookmarks',
                  'delicious type:extension': 'Delicious Bookmarks',
                  'grapple platform:mac': 'GrApple',
                  'delicious/1': 'Delicious Bookmarks',
                  'grapple/all/10/Darwin': 'GrApple',
                  'delicious/all/10/Darwin/3.5': 'Delicious Bookmarks',
                  '/en-US/mobile/api/1.2/search/twitter/all/10/Linux/1.0':
                  'TwitterBar',
                  }

        for url, text in expect.iteritems():
            if not url.startswith('/'):
                url = '/en-US/firefox/api/1.2/search/' + url

            response = self.client.get(url)
            self.assertContains(response, text, msg_prefix=url)

    def test_search_limits(self):
        """
        Test that we limit our results correctly.
        """
        response = self.client.get(
                "/en-US/firefox/api/1.2/search/delicious/all/1")
        eq_(response.content.count("<addon id"), 1)

    def test_total_results(self):
        """
        The search for firefox should result in 2 total addons, even though we
        limit (and therefore show) only 1.
        """
        response = self.client.get(
                "/en-US/firefox/api/1.2/search/firefox/all/1")
        self.assertContains(response, """<searchresults total_results="2">""")
        self.assertContains(response, "</addon>", 1)


class LanguagePacks(UploadTest):
    fixtures = ['addons/listed', 'base/apps']

    def setUp(self):
        self.url = reverse('api.language', args=['1.5'])
        self.tb_url = self.url.replace('firefox', 'thunderbird')
        self.addon = Addon.objects.get(pk=3723)

    def tearDown(self):
        pass

    def test_search_language_pack(self):
        self.addon.update(type=amo.ADDON_LPAPP, status=amo.STATUS_PUBLIC)
        res = self.client.get(self.url)
        self.assertContains(res, "<guid>{835A3F80-DF39")

    def test_search_no_language_pack(self):
        res = self.client.get(self.url)
        self.assertNotContains(res, "<guid>{835A3F80-DF39")

    def test_search_app(self):
        self.addon.update(type=amo.ADDON_LPAPP, status=amo.STATUS_PUBLIC)
        AppSupport.objects.create(addon=self.addon, app_id=amo.THUNDERBIRD.id)
        res = self.client.get(self.tb_url)
        self.assertContains(res, "<guid>{835A3F80-DF39")

    def test_search_no_app(self):
        self.addon.update(type=amo.ADDON_LPAPP, status=amo.STATUS_PUBLIC)
        res = self.client.get(self.tb_url)
        self.assertNotContains(res, "<guid>{835A3F80-DF39")

    def test_search_no_localepicker(self):
        self.addon.update(type=amo.ADDON_LPAPP, status=amo.STATUS_PUBLIC)
        res = self.client.get(self.tb_url)
        self.assertNotContains(res, "<strings><![CDATA[")

    @patch('apps.addons.models.Addon.get_localepicker')
    def test_localepicker(self, get_localepicker):
        get_localepicker.return_value = 'some value'
        self.addon.update(type=amo.ADDON_LPAPP, status=amo.STATUS_PUBLIC)
        res = self.client.get(self.url)
        self.assertContains(res, dedent("""
                                                <strings><![CDATA[
                                            some value
                                                ]]></strings>"""))
