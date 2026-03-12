"""
Production settings
"""
from .base import *  # noqa: F403, F401

DEBUG = False

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Static files (whitenoise)
MIDDLEWARE.insert(  # noqa: F405
    1, 'whitenoise.middleware.WhiteNoiseMiddleware'
)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
