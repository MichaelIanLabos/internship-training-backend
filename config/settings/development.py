"""
Development settings
"""
from .base import *  # noqa: F403, F401

DEBUG = True

# Django Debug Toolbar
if DEBUG:  # noqa: F405
    INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
    MIDDLEWARE += [  # noqa: F405
        'debug_toolbar.middleware.DebugToolbarMiddleware'
    ]
    INTERNAL_IPS = ['127.0.0.1']
