# -*- coding: utf-8 -*-
# Django settings for zamboni project.

import os
import logging
import socket

from django.utils.functional import lazy

try:
    # If we have build ids available, we'll grab them here and add them to our
    # CACHE_PREFIX.  This will let us not have to flush memcache during updates
    # and it will let us preload data into it before a production push.
    from build import BUILD_ID_CSS, BUILD_ID_JS
    build_id = "%s%s" % (BUILD_ID_CSS[:2], BUILD_ID_JS[:2])
except ImportError:
    build_id = ""

# Make filepaths relative to settings.
ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

# We need to track this because hudson can't just call its checkout "zamboni".
# It puts it in a dir called "workspace".  Way to be, hudson.
ROOT_PACKAGE = os.path.basename(ROOT)

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DEBUG_PROPAGATE_EXCEPTIONS = True

# Skip indexing ES to speed things up?
SKIP_SEARCH_INDEX = False

# LESS CSS OPTIONS (Debug only)
LESS_PREPROCESS = False  # Compile LESS with Node, rather than client-side JS?
LESS_LIVE_REFRESH = False  # Refresh the CSS on save?
LESS_BIN = 'lessc'

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS

FLIGTAR = 'amo-admins@mozilla.org'
EDITORS_EMAIL = 'amo-editors@mozilla.org'
SENIOR_EDITORS_EMAIL = 'amo-admin-reviews@mozilla.org'

DATABASES = {
    'default': {
        'NAME': 'zamboni',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '',
        'PORT': '',
        'USER': '',
        'PASSWORD': '',
        'OPTIONS': {'init_command': 'SET storage_engine=InnoDB'},
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    },
}

# A database to be used by the services scripts, which does not use Django.
# The settings can be copied from DATABASES, but since its not a full Django
# database connection, only some values are supported.
SERVICES_DATABASE = {
    'NAME': 'zamboni',
    'USER': '',
    'PASSWORD': '',
    'HOST': '',
}

DATABASE_ROUTERS = ('multidb.PinningMasterSlaveRouter',)

# Put the aliases for your slave databases in this list.
SLAVE_DATABASES = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-US'

# Accepted locales
AMO_LANGUAGES = (
    'af', 'ar', 'bg', 'ca', 'cs', 'da', 'de', 'el', 'en-US', 'es-ES',
    'eu', 'fa', 'fi', 'fr', 'ga-IE', 'he', 'hu', 'id', 'it', 'ja', 'ko', 'mn',
    'nl', 'pl', 'pt-BR', 'pt-PT', 'ro', 'ru', 'sk', 'sl', 'sq', 'sv-SE',
    'tr', 'uk', 'vi', 'zh-CN', 'zh-TW',
)

def lazy_langs():
    from django.conf import settings
    from product_details import product_details
    if not product_details.languages:
        return {}
    return dict([(i.lower(), product_details.languages[i]['native'])
                 for i in AMO_LANGUAGES])

# Where product details are stored see django-mozilla-product-details
PROD_DETAILS_DIR = path('lib/product_json')

# Override Django's built-in with our native names
LANGUAGES = lazy(lazy_langs, dict)()
RTL_LANGUAGES = ('ar', 'fa', 'fa-IR', 'he')

LANGUAGE_URL_MAP = dict([(i.lower(), i) for i in AMO_LANGUAGES])

# Tower / L10n
LOCALE_PATHS = (path('locale'),)
TEXT_DOMAIN = 'messages'
STANDALONE_DOMAINS = [TEXT_DOMAIN, 'javascript']
TOWER_KEYWORDS = {
    '_lazy': None,
}
TOWER_ADD_HEADERS = True

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# The host currently running the site.  Only use this in code for good reason;
# the site is designed to run on a cluster and should continue to support that
HOSTNAME = socket.gethostname()

# The front end domain of the site. If you're not running on a cluster this
# might be the same as HOSTNAME but don't depend on that.  Use this when you
# need the real domain.
DOMAIN = HOSTNAME

# Full base URL for your main site including protocol.  No trailing slash.
#   Example: https://addons.mozilla.org
SITE_URL = 'http://%s' % DOMAIN

# Domain of the services site.  This is where your API, and in-product pages
# live.
SERVICES_DOMAIN = 'services.%s' % DOMAIN

# Full URL to your API service. No trailing slash.
#   Example: https://services.addons.mozilla.org
SERVICES_URL = 'http://%s' % SERVICES_DOMAIN

# When True, the addon API should include performance data.
API_SHOW_PERF_DATA = True

# The domain of the mobile site.
MOBILE_DOMAIN = 'm.%s' % DOMAIN

# The full url of the mobile site.
MOBILE_SITE_URL = 'http://%s' % MOBILE_DOMAIN

OAUTH_CALLBACK_VIEW = 'api.views.request_token_ready'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = path('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to a temporary storage area
TMP_PATH = path('tmp')

# Absolute path to a writable directory shared by all servers. No trailing
# slash.  Example: /data/
NETAPP_STORAGE = TMP_PATH

#  File path for storing XPI/JAR files (or any files associated with an
#  add-on). Example: /mnt/netapp_amo/addons.mozilla.org-remora/files
ADDONS_PATH = NETAPP_STORAGE + '/addons'

# Like ADDONS_PATH but protected by the app. Used for storing files that should
# not be publicly accessible (like disabled add-ons).
GUARDED_ADDONS_PATH = NETAPP_STORAGE + '/guarded-addons'

# Absolute path to a writable directory shared by all servers. No trailing
# slash.
# Example: /data/uploads
UPLOADS_PATH = NETAPP_STORAGE + '/uploads'

# File path for add-on files that get rsynced to mirrors.
# /mnt/netapp_amo/addons.mozilla.org-remora/public-staging
MIRROR_STAGE_PATH = NETAPP_STORAGE + '/public-staging'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin-media/'

# paths that don't require an app prefix
SUPPORTED_NONAPPS = ('admin', 'developers', 'editors', 'img',
                     'jsi18n', 'localizers', 'media', 'robots.txt',
                     'statistics', 'services', 'blocklist')
DEFAULT_APP = 'firefox'

# paths that don't require a locale prefix
SUPPORTED_NONLOCALES = ('img', 'media', 'robots.txt', 'services', 'downloads',
                        'blocklist')

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'r#%9w^o_80)7f%!_ir5zx$tu3mupw9u%&s!)-_q%gy7i+fhx#)'

# Templates

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'session_csrf.context_processor',

    'django.contrib.messages.context_processors.messages',

    'amo.context_processors.app',
    'amo.context_processors.i18n',
    'amo.context_processors.global_settings',
    'amo.context_processors.static_url',
    'webapps.context_processors.is_webapps',
    'jingo_minify.helpers.build_ids',
)

TEMPLATE_DIRS = (
    path('templates'),
)


def JINJA_CONFIG():
    import jinja2
    from django.conf import settings
    from django.core.cache import cache
    config = {'extensions': ['tower.template.i18n', 'amo.ext.cache',
                             'jinja2.ext.do',
                             'jinja2.ext.with_', 'jinja2.ext.loopcontrols'],
              'finalize': lambda x: x if x is not None else ''}
    if False and not settings.DEBUG:
        # We're passing the _cache object directly to jinja because
        # Django can't store binary directly; it enforces unicode on it.
        # Details: http://jinja.pocoo.org/2/documentation/api#bytecode-cache
        # and in the errors you get when you try it the other way.
        bc = jinja2.MemcachedBytecodeCache(cache._cache,
                                           "%sj2:" % settings.CACHE_PREFIX)
        config['cache_size'] = -1  # Never clear the cache
        config['bytecode_cache'] = bc
    return config


MIDDLEWARE_CLASSES = (
    # AMO URL middleware comes first so everyone else sees nice URLs.
    'amo.middleware.TimingMiddleware',
    'commonware.response.middleware.GraphiteRequestTimingMiddleware',
    'commonware.response.middleware.GraphiteMiddleware',
    'amo.middleware.LocaleAndAppURLMiddleware',
    # Mobile detection should happen in Zeus.
    'mobility.middleware.DetectMobileMiddleware',
    'mobility.middleware.XMobileMiddleware',
    'amo.middleware.RemoveSlashMiddleware',

    # Munging REMOTE_ADDR must come before ThreadRequest.
    'commonware.middleware.SetRemoteAddrFromForwardedFor',

    'commonware.middleware.FrameOptionsHeader',
    'commonware.middleware.StrictTransportMiddleware',
    'multidb.middleware.PinningRouterMiddleware',

    'csp.middleware.CSPMiddleware',

    'amo.middleware.CommonMiddleware',
    'amo.middleware.NoVarySessionMiddleware',
    'cake.middleware.CakeCookieMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'commonware.log.ThreadRequestMiddleware',
    'session_csrf.CsrfMiddleware',

    'cake.middleware.CookieCleaningMiddleware',

    # This should come after authentication middleware
    'access.middleware.ACLMiddleware',

    'commonware.middleware.HidePasswordOnException',
)

# Auth
AUTHENTICATION_BACKENDS = (
    'users.backends.AmoUserBackend',
    'cake.backends.SessionBackend',
)
AUTH_PROFILE_MODULE = 'users.UserProfile'

ROOT_URLCONF = '%s.urls' % ROOT_PACKAGE

INSTALLED_APPS = (
    'amo',  # amo comes first so it always takes precedence.
    'access',
    'addons',
    'api',
    'applications',
    'bandwagon',
    'blocklist',
    'browse',
    'compat',
    'cronjobs',
    'csp',
    'devhub',
    'discovery',
    'editors',
    'extras',
    'files',
    'jingo_minify',
    'pages',
    'perf',
    'product_details',
    'reviews',
    'search',
    'sharing',
    'stats',
    'tags',
    'tower',  # for ./manage.py extract
    'translations',
    'users',
    'versions',
    'webapps',
    'zadmin',

    # We need this so the jsi18n view will pick up our locale directory.
    ROOT_PACKAGE,

    'cake',

    # Third party apps
    'djcelery',
    'django_nose',
    'gunicorn',
    'piston',
    'waffle',

    # Django contrib apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
)

# These apps will be removed from INSTALLED_APPS in a production environment.
DEV_APPS = (
    'django_nose',
)

# Tests
TEST_RUNNER = 'test_utils.runner.RadicalTestSuiteRunner'

# If you want to run Selenium tests, you'll need to have a server running.
# Then give this a dictionary of settings.  Something like:
#    'HOST': 'localhost',
#    'PORT': 4444,
#    'BROWSER': '*firefox', # Alternative: *safari
SELENIUM_CONFIG = {}

# Tells the extract script what files to look for l10n in and what function
# handles the extraction.  The Tower library expects this.
DOMAIN_METHODS = {
    'messages': [
        ('apps/**.py',
            'tower.management.commands.extract.extract_tower_python'),
        ('apps/**/templates/**.html',
            'tower.management.commands.extract.extract_tower_template'),
        ('templates/**.html',
            'tower.management.commands.extract.extract_tower_template'),
    ],
    'lhtml': [
        ('**/templates/**.lhtml',
            'tower.management.commands.extract.extract_tower_template'),
    ],
    'javascript': [
        # We can't say **.js because that would dive into mochikit and timeplot
        # and all the other baggage we're carrying.  Timeplot, in particular,
        # crashes the extractor with bad unicode data.
        ('media/js/*.js', 'javascript'),
        ('media/js/amo2009/**.js', 'javascript'),
        ('media/js/zamboni/**.js', 'javascript'),
    ],
}

# Bundles is a dictionary of two dictionaries, css and js, which list css files
# and js files that can be bundled together by the minify app.
MINIFY_BUNDLES = {
    'css': {
        # CSS files common to the entire site.
        'zamboni/css': (
            'css/legacy/main.css',
            'css/legacy/main-mozilla.css',
            'css/legacy/jquery-lightbox.css',
            'css/legacy/autocomplete.css',
            'css/zamboni/zamboni.css',
            'css/global/headerfooter.css',
            'css/zamboni/amo_headerfooter.css',
            'css/zamboni/tags.css',
            'css/zamboni/tabs.css',
        ),
        'zamboni/impala': (
            'css/impala/base.css',
            'css/legacy/jquery-lightbox.css',
            'css/impala/site.less',
            'css/impala/typography.less',
            'css/global/headerfooter.css',
            'css/impala/forms.less',
            'css/impala/header.less',
            'css/impala/footer.less',
            'css/impala/moz-tab.css',
            'css/impala/hovercards.less',
            'css/impala/toplist.less',
            'css/impala/carousel.less',
            'css/impala/reviews.less',
            'css/impala/buttons.less',
            'css/impala/promos.less',
            'css/impala/addon_details.less',
            'css/impala/policy.less',
            'css/impala/expando.less',
            'css/impala/popups.less',
            'css/impala/l10n.less',
            'css/impala/contributions.less',
            'css/impala/lightbox.less',
            'css/impala/prose.less',
            'css/impala/sharing.less',
            'css/impala/abuse.less',
            'css/impala/paginator.less',
            'css/impala/listing.less',
            'css/impala/users.less',
            'css/impala/collections.less',
            'css/impala/tooltips.less',
            'css/impala/search.less',
        ),
        'zamboni/discovery-pane': (
            'css/zamboni/discovery-pane.css',
            'css/impala/promos.less',
            'css/legacy/jquery-lightbox.css',
        ),
        'zamboni/devhub': (
            'css/zamboni/developers.css',
            'css/zamboni/docs.less',
        ),
        'zamboni/devhub_impala': (
            'css/impala/developers.less',
        ),
        'zamboni/editors': (
            'css/zamboni/editors.css',
        ),
        'zamboni/files': (
            'css/lib/syntaxhighlighter/shCoreDefault.css',
            'css/zamboni/files.css',
        ),
        'zamboni/mobile': (
            'css/zamboni/mobile.css',
        ),
    },
    'js': {
        # JS files common to the entire site.
        'common': (
            'js/lib/jquery-1.4.2.min.js',
            'js/lib/jquery-ui/custom-1.8.5.min.js',
            'js/lib/underscore-min.js',
            'js/zamboni/browser.js',
            'js/amo2009/addons.js',
            'js/zamboni/init.js',
            'js/zamboni/format.js',
            'js/zamboni/buttons.js',
            'js/zamboni/tabs.js',

            'js/lib/jquery.cookie.js',
            'js/zamboni/storage.js',
            'js/zamboni/global.js',
            'js/amo2009/global.js',
            'js/impala/ratingwidget.js',
            'js/lib/jquery-ui/jqModal.js',
            'js/amo2009/home.js',
            'js/zamboni/l10n.js',
            'js/zamboni/debouncer.js',

            # Homepage
            'js/zamboni/homepage.js',

            # Add-ons details page
            'js/lib/jquery-ui/ui.lightbox.js',
            'js/get-satisfaction-v2.js',
            'js/zamboni/contributions.js',
            'js/zamboni/addon_details.js',
            'js/impala/abuse.js',
            'js/zamboni/reviews.js',

            # Personas
            'js/lib/jquery.hoverIntent.min.js',
            'js/zamboni/personas_core.js',
            'js/zamboni/personas.js',

            # Collections
            'js/zamboni/collections.js',

            # Performance
            'js/zamboni/perf.js',

            # Users
            'js/zamboni/users.js',

            # Fix-up outgoing links
            'js/zamboni/outgoing_links.js',

            # Hover delay for global header
            'js/global/menu.js',

            # Password length and strength
            'js/zamboni/password-strength.js'
        ),
        'impala': (
            'js/lib/jquery-1.6.min.js',
            'js/lib/jquery-ui/custom-1.8.5.min.js',
            'js/lib/underscore-min.js',
            'js/impala/carousel.js',
            'js/zamboni/browser.js',
            'js/amo2009/addons.js',
            'js/zamboni/init.js',
            'js/zamboni/format.js',
            'js/zamboni/buttons.js',

            'js/lib/jquery.cookie.js',
            'js/zamboni/storage.js',
            'js/zamboni/truncation.js',
            'js/zamboni/global.js',
            'js/impala/global.js',
            'js/impala/ratingwidget.js',
            'js/lib/jquery-ui/jqModal.js',
            'js/zamboni/l10n.js',

            # Homepage
            'js/impala/homepage.js',

            # Add-ons details page
            'js/lib/jquery-ui/ui.lightbox.js',
            'js/get-satisfaction-v2.js',
            'js/zamboni/contributions.js',
            'js/impala/addon_details.js',
            'js/impala/abuse.js',
            'js/impala/reviews.js',

            # Personas
            'js/lib/jquery.hoverIntent.min.js',
            'js/zamboni/personas_core.js',
            'js/zamboni/personas.js',

            # Collections
            'js/zamboni/collections.js',
            'js/impala/collections.js',

            # Performance
            'js/zamboni/perf.js',

            # Users
            'js/zamboni/users.js',
            'js/impala/users.js',

            # Fix-up outgoing links
            'js/zamboni/outgoing_links.js',
        ),
        'zamboni/discovery': (
            'js/lib/jquery-1.4.2.min.js',
            'js/lib/underscore-min.js',
            'js/zamboni/browser.js',
            'js/zamboni/init.js',
            'js/zamboni/format.js',
            'js/impala/carousel.js',

            # Add-ons details
            'js/zamboni/buttons.js',
            'js/lib/jquery-ui/ui.lightbox.js',

            # Personas
            'js/lib/jquery.hoverIntent.min.js',
            'js/zamboni/personas_core.js',
            'js/zamboni/personas.js',

            'js/zamboni/debouncer.js',
            'js/zamboni/truncation.js',
            'js/lib/jquery.cookie.js',
            'js/zamboni/storage.js',
            'js/zamboni/discovery_addons.js',
            'js/zamboni/discovery_pane.js',
        ),
        'zamboni/devhub': (
            'js/zamboni/truncation.js',
            'js/zamboni/upload.js',
            'js/zamboni/devhub.js',
            'js/zamboni/validator.js',
            'js/zamboni/packager.js',
        ),
        'zamboni/editors': (
            'js/zamboni/editors.js',
            'js/lib/highcharts.src.js'
        ),
        'zamboni/files': (
            'js/lib/diff_match_patch_uncompressed.js',
            'js/lib/syntaxhighlighter/xregexp-min.js',
            'js/lib/syntaxhighlighter/shCore.js',
            'js/lib/syntaxhighlighter/shLegacy.js',
            'js/lib/syntaxhighlighter/shBrushAppleScript.js',
            'js/lib/syntaxhighlighter/shBrushAS3.js',
            'js/lib/syntaxhighlighter/shBrushBash.js',
            'js/lib/syntaxhighlighter/shBrushCpp.js',
            'js/lib/syntaxhighlighter/shBrushCSharp.js',
            'js/lib/syntaxhighlighter/shBrushCss.js',
            'js/lib/syntaxhighlighter/shBrushDiff.js',
            'js/lib/syntaxhighlighter/shBrushJava.js',
            'js/lib/syntaxhighlighter/shBrushJScript.js',
            'js/lib/syntaxhighlighter/shBrushPhp.js',
            'js/lib/syntaxhighlighter/shBrushPlain.js',
            'js/lib/syntaxhighlighter/shBrushPython.js',
            'js/lib/syntaxhighlighter/shBrushSass.js',
            'js/lib/syntaxhighlighter/shBrushSql.js',
            'js/lib/syntaxhighlighter/shBrushVb.js',
            'js/lib/syntaxhighlighter/shBrushXml.js',
            'js/zamboni/files.js',
        ),
        'zamboni/mobile': (
            'js/lib/jquery-1.5.min.js',
            'js/lib/jqmobile.js',
            'js/lib/jquery.cookie.js',
            'js/zamboni/browser.js',
            'js/zamboni/init.js',
            'js/zamboni/format.js',
            'js/zamboni/mobile/buttons.js',
            'js/zamboni/truncation.js',
            'js/zamboni/personas_core.js',
            'js/zamboni/mobile/personas.js',
            'js/zamboni/mobile/general.js',
        ),
        'zamboni/stats': (
            'js/lib/jquery-datepicker.js',
            'js/lib/highcharts.src.js',
            'js/zamboni/stats/csv_keys.js',
            'js/zamboni/stats/helpers.js',
            'js/zamboni/stats/stats_manager.js',
            'js/zamboni/stats/stats_tables.js',
            'js/zamboni/stats/stats.js',
        ),
        # This is included when DEBUG is True.  Bundle in <head>.
        'debug': (
            'js/debug/less_setup.js',
            'js/lib/less-1.0.41.js',
            'js/debug/less_live.js',
        ),
    }
}


# Caching
# Prefix for cache keys (will prevent collisions when running parallel copies)
CACHE_PREFIX = 'amo:%s:' % build_id
FETCH_BY_ID = True

# Number of seconds a count() query should be cached.  Keep it short because
# it's not possible to invalidate these queries.
CACHE_COUNT_TIMEOUT = 60

# External tools.
SPHINX_INDEXER = 'indexer'
SPHINX_SEARCHD = 'searchd'
SPHINX_CONFIG_PATH = path('configs/sphinx/sphinx.conf')
SPHINX_CATALOG_PATH = TMP_PATH + '/data/sphinx'
SPHINX_LOG_PATH = TMP_PATH + '/log/searchd'
SPHINX_HOST = '127.0.0.1'
SPHINX_PORT = 3312
SPHINXQL_PORT = 3307

TEST_SPHINX_PORT = 3412
TEST_SPHINXQL_PORT = 3407
TEST_SPHINX_CATALOG_PATH = TMP_PATH + '/test/data/sphinx'
TEST_SPHINX_LOG_PATH = TMP_PATH + '/test/log/searchd'

SPHINX_TIMEOUT = 1

JAVA_BIN = '/usr/bin/java'

# Add-on download settings.
MIRROR_DELAY = 30  # Minutes before we serve downloads from mirrors.
MIRROR_URL = 'http://releases.mozilla.org/pub/mozilla.org/addons'
LOCAL_MIRROR_URL = 'https://static.addons.mozilla.net/_files'
PRIVATE_MIRROR_URL = '/_privatefiles'

# File paths
ADDON_ICONS_PATH = UPLOADS_PATH + '/addon_icons'
COLLECTIONS_ICON_PATH = UPLOADS_PATH + '/collection_icons'
PREVIEWS_PATH = UPLOADS_PATH + '/previews'
USERPICS_PATH = UPLOADS_PATH + '/userpics'
PACKAGER_PATH = os.path.join(TMP_PATH, 'packager')
ADDON_ICONS_DEFAULT_PATH = os.path.join(MEDIA_ROOT, 'img/addon-icons')

PREVIEW_THUMBNAIL_PATH = (PREVIEWS_PATH + '/thumbs/%s/%d.png')
PREVIEW_FULL_PATH = (PREVIEWS_PATH + '/full/%s/%d.png')

# URL paths
# paths for images, e.g. mozcdn.com/amo or '/static'
STATIC_URL = SITE_URL
ADDON_ICONS_DEFAULT_URL = MEDIA_URL + '/img/addon-icons'
ADDON_ICON_BASE_URL = MEDIA_URL + 'img/icons/'
ADDON_ICON_URL = ('%s/images/addon_icon/%%d-%%d.png?modified=%%s' %
                  STATIC_URL)
PREVIEW_THUMBNAIL_URL = (STATIC_URL +
        '/img/uploads/previews/thumbs/%s/%d.png?modified=%d')
PREVIEW_FULL_URL = (STATIC_URL +
        '/img/uploads/previews/full/%s/%d.png?modified=%d')
USERPICS_URL = STATIC_URL + '/img/uploads/userpics/%s/%s/%s.png?modified=%d'
# paths for uploaded extensions
COLLECTION_ICON_URL = ('%s/images/collection_icon/%%s.png?modified=%%s' %
                       STATIC_URL)
PERSONAS_IMAGE_URL = ('http://www.getpersonas.com/static/'
                      '%(tens)d/%(units)d/%(id)d/%(file)s')
PERSONAS_IMAGE_URL_SSL = ('https://www.getpersonas.com/static/'
                          '%(tens)d/%(units)d/%(id)d/%(file)s')
PERSONAS_USER_ROOT = 'http://www.getpersonas.com/gallery/designer/%s'
PERSONAS_UPDATE_URL = 'https://www.getpersonas.com/update_check/%d'

# Outgoing URL bouncer
REDIRECT_URL = 'http://outgoing.mozilla.org/v1/'
REDIRECT_SECRET_KEY = ''

# Default to short expiration; check "remember me" to override
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 1209600
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_DOMAIN = ".%s" % DOMAIN  # bug 608797
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# These should have app+locale at the start to avoid redirects
LOGIN_URL = "/users/login"
LOGOUT_URL = "/users/logout"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Legacy Settings
# used by old-style CSRF token
CAKE_SESSION_TIMEOUT = 8640

# PayPal Settings
PAYPAL_API_URL = 'https://api-3t.paypal.com/nvp'
PAYPAL_API_VERSION = '50'
PAYPAL_APP_ID = ''
PAYPAL_BN = ''
PAYPAL_CGI_URL = 'https://www.paypal.com/cgi-bin/webscr'
PAYPAL_CGI_AUTH = {'USER': '', 'PASSWORD': '', 'SIGNATURE': ''}

PAYPAL_PAY_URL = 'https://svcs.paypal.com/AdaptivePayments/Pay'
PAYPAL_FLOW_URL = 'https://paypal.com/webapps/adaptivepayment/flow/pay'
PAYPAL_JS_URL = 'https://www.paypalobjects.com/js/external/dg.js'
PAYPAL_EMBEDDED_AUTH = {'USER': '', 'PASSWORD': '', 'SIGNATURE': ''}
PAYPAL_EMAIL = ''

# Paypal is an awful place that doesn't understand locales.  Instead they have
# country codes.  This maps our locales to their codes.
PAYPAL_COUNTRYMAP = {
    'af': 'ZA', 'ar': 'EG', 'ca': 'ES', 'cs': 'CZ', 'cy': 'GB', 'da': 'DK',
    'de': 'DE', 'de-AT': 'AT', 'de-CH': 'CH', 'el': 'GR', 'en-GB': 'GB',
    'eu': 'BS', 'fa': 'IR', 'fi': 'FI', 'fr': 'FR', 'he': 'IL', 'hu': 'HU',
    'id': 'ID', 'it': 'IT', 'ja': 'JP', 'ko': 'KR', 'mn': 'MN', 'nl': 'NL',
    'pl': 'PL', 'ro': 'RO', 'ru': 'RU', 'sk': 'SK', 'sl': 'SI', 'sq': 'AL',
    'sr': 'CS', 'tr': 'TR', 'uk': 'UA', 'vi': 'VI',
}

# Contribution limit, one time and monthly
MAX_CONTRIBUTION = 1000

# Email settings
DEFAULT_FROM_EMAIL = "Mozilla Add-ons <nobody@mozilla.org>"

# Email goes to the console by default.  s/console/smtp/ for regular delivery
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Please use all lowercase for the blacklist.
EMAIL_BLACKLIST = (
    'nobody@mozilla.org',
)


## Celery
BROKER_HOST = 'localhost'
BROKER_PORT = 5672
BROKER_USER = 'zamboni'
BROKER_PASSWORD = 'zamboni'
BROKER_VHOST = 'zamboni'
BROKER_CONNECTION_TIMEOUT = 0.1
CELERY_RESULT_BACKEND = 'amqp'
CELERY_IGNORE_RESULT = True
CELERY_IMPORTS = ('django_arecibo.tasks',)
# We have separate celeryds for processing devhub & images as fast as possible
# Some notes:
# - always add routes here instead of @task(queue=<name>)
# - when adding a queue, be sure to update deploy.py so that it gets restarted
CELERY_ROUTES = {
    'devhub.tasks.validator': {'queue': 'devhub'},
    'devhub.tasks.compatibility_check': {'queue': 'devhub'},
    'devhub.tasks.file_validator': {'queue': 'devhub'},
    'devhub.tasks.packager': {'queue': 'devhub'},
    'bandwagon.tasks.resize_icon': {'queue': 'images'},
    'users.tasks.resize_photo': {'queue': 'images'},
    'users.tasks.delete_photo': {'queue': 'images'},
    'devhub.tasks.resize_icon': {'queue': 'images'},
    'devhub.tasks.resize_preview': {'queue': 'images'},
    'zadmin.tasks.bulk_validate_file': {'queue': 'bulk'},
    'devhub.tasks.flag_binary': {'queue': 'bulk'},
}

# When testing, we always want tasks to raise exceptions. Good for sanity.
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


## Fixture Magic
CUSTOM_DUMPS = {
    'addon': {  # ./manage.py custom_dump addon id
        'primary': 'addons.addon',  # This is our reference model.
        'dependents': [  # These are items we wish to dump.
            # Magic turns this into current_version.files.all()[0].
            'current_version.files.all.0',
            'current_version.apps.all.0',
            'addonuser_set.all.0',
        ],
        'order': ('applications.application', 'translations.translation',
                  'addons.addontype', 'files.platform', 'addons.addon',
                  'versions.license', 'versions.version', 'files.file'),
        'excludes': {
            'addons.addon': ('_current_version',),
        }
    }
}

## Hera (http://github.com/clouserw/hera)
HERA = [{'USERNAME': '',
        'PASSWORD': '',
        'LOCATION': '',
       }]

# Logging
LOG_LEVEL = logging.DEBUG
HAS_SYSLOG = True  # syslog is used if HAS_SYSLOG and NOT DEBUG.
SYSLOG_TAG = "http_app_addons"
SYSLOG_TAG2 = "http_app_addons2"
SYSLOG_CSP = "http_app_addons_csp"
# See PEP 391 and log_settings.py for formatting help.  Each section of
# LOGGING will get merged into the corresponding section of
# log_settings.py. Handlers and log levels are set up automatically based
# on LOG_LEVEL and DEBUG unless you set them here.  Messages will not
# propagate through a logger unless propagate: True is set.
LOGGING_CONFIG = None
LOGGING = {
    'loggers': {
        'amqplib': {'handlers': ['null']},
        'caching.invalidation': {'handlers': ['null']},
        'caching': {'level': logging.WARNING},
        'pyes': {'handlers': ['null']},
        'rdflib': {'handlers': ['null']},
        'suds': {'handlers': ['null']},
        'z.sphinx': {'level': logging.INFO},
        'z.task': {'level': logging.INFO},
    },
}

# CSP Settings
CSP_REPORT_URI = '/services/csp/report'
CSP_POLICY_URI = '/services/csp/policy?build=%s' % build_id
CSP_REPORT_ONLY = True

CSP_ALLOW = ("'self'",)
CSP_IMG_SRC = ("'self'", STATIC_URL,
               "https://www.google.com",  # Recaptcha comes from google
               "https://statse.webtrendslive.com",
               "https://www.getpersonas.com",
               "https://s3.amazonaws.com",  # getsatisfaction
              )
CSP_SCRIPT_SRC = ("'self'", STATIC_URL,
                  "https://www.google.com",  # Recaptcha
                  "https://www.paypalobjects.com",
                  )
CSP_STYLE_SRC = ("'self'", STATIC_URL,)
CSP_OBJECT_SRC = ("'none'",)
CSP_MEDIA_SRC = ("'none'",)
CSP_FRAME_SRC = ("https://s3.amazonaws.com",  # getsatisfaction
                 "https://getsatisfaction.com",  # getsatisfaction
                )
CSP_FONT_SRC = ("'self'", "fonts.mozilla.com", "www.mozilla.com", )
# self is needed for paypal which sends x-frame-options:allow when needed.
# x-frame-options:DENY is sent the rest of the time.
CSP_FRAME_ANCESTORS = ("'self'",)


# Should robots.txt deny everything or disallow a calculated list of URLs we
# don't want to be crawled?  Default is false, disallow everything.
# Also see http://www.google.com/support/webmasters/bin/answer.py?answer=93710
ENGAGE_ROBOTS = False

# Read-only mode setup.
READ_ONLY = False


# Turn on read-only mode in settings_local.py by putting this line
# at the VERY BOTTOM: read_only_mode(globals())
def read_only_mode(env):
    env['READ_ONLY'] = True

    # Replace the default (master) db with a slave connection.
    if not env.get('SLAVE_DATABASES'):
        raise Exception("We need at least one slave database.")
    slave = env['SLAVE_DATABASES'][0]
    env['DATABASES']['default'] = env['DATABASES'][slave]

    # No sessions without the database, so disable auth.
    env['AUTHENTICATION_BACKENDS'] = ('users.backends.NoAuthForYou',)

    # Add in the read-only middleware before csrf middleware.
    extra = 'amo.middleware.ReadOnlyMiddleware'
    before = 'session_csrf.CsrfMiddleware'
    m = list(env['MIDDLEWARE_CLASSES'])
    m.insert(m.index(before), extra)
    env['MIDDLEWARE_CLASSES'] = tuple(m)


# Uploaded file limits
MAX_ICON_UPLOAD_SIZE = 4 * 1024 * 1024
MAX_PHOTO_UPLOAD_SIZE = MAX_ICON_UPLOAD_SIZE

# RECAPTCHA - copy all three statements to settings_local.py
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_URL = ('https://www.google.com/recaptcha/api/challenge?k=%s' %
                 RECAPTCHA_PUBLIC_KEY)

# Send Django signals asynchronously on a background thread.
ASYNC_SIGNALS = True

# Performance notes on add-ons
PERFORMANCE_NOTES = False

# Used to flag slow addons.
# If slowness of addon is THRESHOLD percent slower, show a warning.
PERF_THRESHOLD = 25

REDIS_BACKENDS = {'master': 'redis://localhost:6379?socket_timeout=0.5'}

# Directory of JavaScript test files for django_qunit to run
QUNIT_TEST_DIRECTORY = os.path.join(MEDIA_ROOT, 'js', 'zamboni', 'tests')

# Full path or executable path (relative to $PATH) of the spidermonkey js
# binary.  It must be a version compatible with amo-validator
SPIDERMONKEY = None
VALIDATE_ADDONS = True

# When True include full tracebacks in JSON. This is useful for QA on preview.
EXPOSE_VALIDATOR_TRACEBACKS = False

# Feature flags
SEARCH_EXCLUDE_PERSONAS = True
UNLINK_SITE_STATS = True

# Use the new featured add-ons system which makes use of featured collections.
NEW_FEATURES = False

# Impala flags.
IMPALA_BROWSE = False
IMPALA_REVIEWS = False
IMPALA_MEET = False  # Meet the Developer page.

FASTER_GUID_SEARCH = True

# Set to True if we're allowed to use X-SENDFILE.
XSENDFILE = True

MOBILE_COOKIE = 'mamo'

# If the users's Firefox has a version number greater than this we consider it
# a beta.
MIN_BETA_VERSION = '3.7'

DEFAULT_SUGGESTED_CONTRIBUTION = 5

# Path to `ps`.
PS_BIN = '/bin/ps'

BLOCKLIST_COOKIE = 'BLOCKLIST_v1'

# Responsys id used for newsletter subscribing
RESPONSYS_ID = ''

# The maximum file size that is shown inside the file viewer.
FILE_VIEWER_SIZE_LIMIT = 1048576
# The maximum file size that you can have inside a zip file.
FILE_UNZIP_SIZE_LIMIT = 104857600

# How long to delay modify updates to cope with alleged NFS slowness.
MODIFIED_DELAY = 3

# This is a list of dictionaries that we should generate compat info for.
# app: should match amo.FIREFOX.id.
# main: the app version we're generating compat info for.
# versions: version numbers to show in comparisons.
# previous: the major version before :main.
COMPAT = (
    dict(app=1, main='8.0', versions=('8.0', '8.0a2', '8.0a1'), previous='7.0'),
    dict(app=1, main='7.0', versions=('7.0', '7.0a2', '7.0a1'), previous='6.0'),
    dict(app=1, main='6.0', versions=('6.0', '6.0a2', '6.0a1'), previous='5.0'),
    dict(app=1, main='5.0', versions=('5.0', '5.0a2', '5.0a1'), previous='4.0'),
    dict(app=1, main='4.0', versions=('4.0', '4.0a1', '3.7a'), previous='3.6'),
)

# URL for reporting arecibo errors too. If not set, won't be sent.
ARECIBO_SERVER_URL = ""

# A whitelist of domains that the authentication script will redirect to upon
# successfully logging in or out.
VALID_LOGIN_REDIRECTS = {
    'builder': 'https://builder.addons.mozilla.org',
    'builderstage': 'https://builder-addons-next.allizom.org',
    'buildertrunk': 'https://builder-addons.allizom.org',
}

# Secret key we send to builder so we can trust responses from the builder.
BUILDER_SECRET_KEY = 'love will tear us apart'
# The builder URL we hit to upgrade jetpacks.
BUILDER_UPGRADE_URL = 'https://addons.mozilla.org/services/builder'


## Elastic Search
ES_HOSTS = ['127.0.0.1:9200']
ES_INDEX = 'amo'
USE_ELASTIC = True

# Default AMO user id to use for tasks.
TASK_USER_ID = 4757633

# If this is False, tasks and other jobs that send non-critical emails should
# use a fake email backend.
SEND_REAL_EMAIL = False

STATSD_HOST = 'localhost'
STATSD_PORT = 8125
STATSD_PREFIX = 'amo'

GRAPHITE_HOST = 'localhost'
GRAPHITE_PORT = 2003
GRAPHITE_PREFIX = 'amo'
GRAPHITE_TIMEOUT = 1

# URL to the service that triggers addon performance tests.  See devhub.perf.
PERF_TEST_URL = 'http://areweperftestingyet.com/trigger.cgi'

# IP addresses of servers we use as proxies.
KNOWN_PROXIES = []

# Blog URL
DEVELOPER_BLOG_URL = 'http://blog.mozilla.com/addons/feed/'

LOGIN_RATELIMIT_USER = 5
LOGIN_RATELIMIT_ALL_USERS = '15/m'
