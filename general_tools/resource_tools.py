import os
import re


def tryint(s):
    try:
        return int(s)
    except:
        return s


def alphanum_key(s):
    return [tryint(c) for c in re.split('([0-9]+)', s)]


def sort_alphanumeric(l):
    l.sort(key=alphanum_key)


def get_latest_version(path_to_versions):
    versions = [d for d in os.listdir(path_to_versions) if re.match(r'^v\d+', d) and
                os.path.isdir(os.path.join(path_to_versions, d))]
    if versions and len(versions):
        sort_alphanumeric(versions)
        return versions[-1]


def get_latest_version_path(path_to_versions):
    latest_version = get_latest_version(path_to_versions)
    if latest_version:
        return os.path.join(path_to_versions, latest_version)
    else:
        return path_to_versions
