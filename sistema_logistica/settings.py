"""
Django settings for sistema_logistica project.
"""

from pathlib import Path
import os 

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-=%%*3whr#t3ute)p06j)v01b=72lw*npsanv#d(u1=z^xu#fy4'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# 🚀 AJUSTE NECESSÁRIO AQUI: Permitir hosts locais para o desenvolvimento
ALLOWED_HOSTS = [
    '127.0.0.1', 
    'localhost', 
    '10.0.2.2'
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps de Terceiros Necessários
    'django.contrib.humanize', 
    
    'widget_tweaks', 
    
    
    # --- Seus Apps Customizados ---
    'core', 
    'onhold',
    'rastreio',
    'collection_pool', 
    'parcel_sweeper',
    'parcel_lost',
    'inventory_analysis',
    'expedicao', 
    'conferencia',
    'apresentacao',
    'logistica',

    # ------------------------------
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sistema_logistica.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # ✅ AJUSTE FINAL E MAIS ROBUSTO: Usando os.path.join.
        'DIRS': [
            os.path.join(BASE_DIR, 'core', 'templates'), # Caminho para 'base.html'
            os.path.join(BASE_DIR, 'templates'),         # Caminho para templates na raiz (fallback)
        ], 
        'APP_DIRS': True, 
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema_logistica.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- CONFIGURAÇÕES DO USUÁRIO PERSONALIZADO ---
# Indica ao Django para usar o modelo Usuario que criamos no app 'core'
AUTH_USER_MODEL = 'core.Usuario' 

# Configuração simples para redirecionamento após login/logout
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
# ----------------------------------------------


# --- CONFIGURAÇÕES DE MÍDIA E UPLOAD ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# ------------------------------------------------------------------