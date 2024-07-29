import storelsb
from pathlib import Path

from setuptools import find_packages
from setuptools import setup
from setuptools.command.install import install
from shellsy import __version__ as version
import os

project_dir = Path(__file__).parent


class ShellsyInstallCommand(install):
    def run(self):
        import shellsy.settings

        shellsy.settings.init()
        super().run()


try:
    long_description = (project_dir / "README.md").read_text()
except FileNotFoundError:
    try:
        long_description = Path("README.md").read_text()
    except FileNotFoundError:
        try:
            long_description = Path("/src/README.md").read_text()
        except FileNotFoundError:
            long_description = (project_dir.parent / "README.md").read_text()


setup(
    name='storelsb',
    version=storelsb.__version__,
    packages=['storelsb'],
    license="MIT",
    author='ken-morel',
    description='A sample shellsy plugin',
    install_requires=[],
    classifiers=[
        # See https://pypi.org/classifiers/
        "Intended Audience :: Developers",
        'Development Status :: 1 - Planning',
        # "Development Status :: 2 - Pre-Alpha",
        # "Development Status :: 3 - Alpha",
        # 'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
