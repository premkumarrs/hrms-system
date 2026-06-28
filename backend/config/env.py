"""Environment variable helpers for HRMS settings."""

import os
from pathlib import Path


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=None, separator=','):
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return list(default or [])
    return [item.strip() for item in value.split(separator) if item.strip()]


def env_int(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return default
    return int(value)


def env_path(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return Path(default)
    return Path(value)
