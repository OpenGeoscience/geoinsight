from pathlib import Path

from setuptools import find_packages, setup

__version__ = '1.20.1'

readme_file = Path(__file__).parent / 'README.md'
if readme_file.exists():
    with readme_file.open() as f:
        long_description = f.read()
else:
    # When this is first installed in development Docker, README.md is not available
    long_description = ''

setup(
    name='geoinsight',
    version=__version__,
    description='',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='Apache 2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    keywords='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django :: 3.0',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python',
    ],
    python_requires='>=3.10',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Pinned August 2024
        'celery==5.4.0',
        'channels[daphne]==4.2.0',  # added March 2025 for analytics
        'channels-redis==4.2.1',  # added March 2025 for analytics
        'django==5.2.8',
        'django-configurations[database,email]==2.5.1',
        'django-extensions==3.2.3',
        'django-filter==24.3',
        'django-guardian==2.4.0',
        'django-oauth-toolkit==2.4.0',
        'djangorestframework==3.15.2',
        'django-large-image==0.10.2',
        'drf-yasg==1.21.11',
        # gdal 3.10 is the newest supported by Django:
        # https://docs.djangoproject.com/en/5.2/ref/contrib/gis/install/geolibs/
        'gdal==3.10.*',
        'large-image[gdal]==1.33.3',
        'large-image-converter==1.33.3',
        'matplotlib==3.9.2',  # for raster colormaps
        'geopandas==1.1.1',
        'networkx==3.3',
        'numpy==2.2.6',
        'pooch[progress]==1.8.2',
        'psycopg[pool]',
        'pyshp==2.3.1',
        'rasterio==1.3.11',
        'urllib3==1.26.15',
        'webcolors==24.6.0',
        # Production only
        'django-composed-configuration[prod]==0.25.0',
        'django-s3-file-field[s3]==1.0.1',
        'gunicorn==22.0.0',
    ],
    extras_require={
        'dev': [
            'django-composed-configuration[dev]==0.25.0',
            'django-debug-toolbar==4.4.6',
            'django-s3-file-field[minio]==1.0.1',
            'ipython==8.26.0',
            'tox==4.16.0',
            'pre-commit==4.0.1',
        ],
        'tasks': [
            'geoai-py==0.9.2',
            'osmnx==2.0.6',
        ],
        'test': [
            'factory-boy==3.3.1',
            'pytest==8.3.3',
            'pytest-django==4.9.0',
            'pytest-mock==3.14.0',
            'django-s3-file-field-client==1.1.0',
        ],
    },
)
