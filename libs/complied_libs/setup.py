from distutils.core import setup

from Cython.Build import cythonize

setup(ext_modules=cythonize('optimized_libs.pyx', annotate=True, language_level=3))
