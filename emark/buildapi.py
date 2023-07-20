"""Extends flit_scm to compile gettext translations before building wheels."""

import glob
import subprocess  # nosec
from pathlib import Path

from flit_scm import buildapi


def compile_gettext_translations():
    print("\33[1m* Compiling gettext translations...\33[0m")
    info = buildapi.read_flit_config(buildapi.pyproj_toml)
    pattern = f"{info.module}/locale/*/LC_MESSAGES/django.po"
    for file in glob.glob(pattern):
        file = Path(file)
        cmd = ["msgfmt", "-c", "-o", file.parent / f"{file.stem}.mo", file]
        subprocess.check_output(cmd)  # nosec


build_sdist = buildapi.build_sdist


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    compile_gettext_translations()
    return buildapi.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    compile_gettext_translations()
    return buildapi.build_editable(wheel_directory, config_settings, metadata_directory)
