#!/usr/bin/env python3
# -*- coding: utf8 -*-
#
#  Copyright (c) 2020 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

"""
Class for a resource
"""
import os
import git
import shutil
from collections import OrderedDict
from datetime import datetime
from general_tools.url_utils import download_file
from general_tools.file_utils import load_yaml_object
from obs_ts_to_md_converter import do_preprocess

DEFAULT_OWNER = 'unfoldingWord'
DEFAULT_REF = 'master'
OWNERS = [DEFAULT_OWNER, 'STR', 'Door43-Catalog', 'PCET', 'EXEGETICAL-BCS']
LOGO_MAP = {
    'sn': 'utn',
    'sq': 'utq',
    'ta': 'uta',
    'tn': 'utn',
    'tw': 'utw',
    'tq': 'utq',
    'obs-tn': 'obs',
    'obs-sn': 'obs',
    'obs-sq': 'obs'
}


class Resource(object):

    def __init__(self, resource_name, repo_name, ref=DEFAULT_REF, owner=DEFAULT_OWNER, manifest=None, url=None,
                 logo_url=None, offline=False, update=True, background_resource=False):
        self.resource_name = resource_name
        self.repo_name = repo_name
        self.ref = ref
        self.owner = owner
        self._manifest = manifest
        self.url = url
        self._logo_url = logo_url
        self.offline = offline
        self.update = not offline and update
        self.background_resource = background_resource

        self.repo_dir = None
        self.repo = None
        self.new_commits = False

    @property
    def logo_url(self):
        if not self._logo_url:
            if self.resource_name in LOGO_MAP:
                logo = LOGO_MAP[self.resource_name]
            else:
                logo = self.resource_name
            self._logo_url = f'https://cdn.door43.org/assets/uw-icons/logo-{logo}-256.png'
        return self._logo_url

    @property
    def logo_file(self):
        return os.path.basename(self.logo_url)

    @staticmethod
    def get_resource_git_url(resource, owner):
        return f'https://git.door43.org/{owner}/{resource}.git'

    def clone(self, working_dir):
        if not self.url:
            self.url = self.get_resource_git_url(self.repo_name, self.owner)
        self.repo_dir = os.path.join(working_dir, self.repo_name)
        if not self.offline and not os.path.exists(self.repo_dir):
            try:
                self.repo = git.Repo.clone_from(self.url, self.repo_dir, depth=1)
            except git.GitCommandError as orig_err:
                owners = OWNERS
                for owner_idx, owner in enumerate(owners):
                    self.url = self.get_resource_git_url(self.repo_name, owner)
                    self.repo_dir = os.path.join(working_dir, owner, self.repo_name)
                    try:
                        self.repo = git.Repo.clone_from(self.url, self.repo_dir, depth=1)
                        self.owner = owner
                    except git.GitCommandError:
                        if owner_idx + 1 == len(owners):
                            raise orig_err
                        else:
                            continue
                    if os.path.exists(self.repo_dir):
                        break
        if not self.repo:
            self.repo = git.Repo(self.repo_dir)
        if self.update:
            for remote in self.repo.remotes:
                remote.fetch()
        if not self.ref:
            self.ref = self.latest_tag
            if not self.ref:
                self.ref = DEFAULT_REF
        self.repo.git.checkout(self.ref)
        if self.ref == DEFAULT_REF and self.update:
            self.repo.git.pull()

        if self.resource_name == 'obs' and \
                not os.path.exists(os.path.join(self.repo_dir, 'manifest.yaml')) and \
                os.path.exists(os.path.join(self.repo_dir, 'manifest.json')) and \
                os.path.exists(os.path.join(self.repo_dir, '01', '01.txt')):
            new_repo_dir = self.repo_dir + '_rc'
            if os.path.exists(new_repo_dir):
                shutil.rmtree(new_repo_dir)
            do_preprocess(self.repo_dir, new_repo_dir)
            download_file('https://git.door43.org/api/v1/repos/unfoldingword/en_obs/raw/LICENSE.md',
                          os.path.join(new_repo_dir, 'LICENSE.md'))
            download_file('https://git.door43.org/api/v1/repos/unfoldingword/en_obs/raw/LICENSE.md',
                          os.path.join(new_repo_dir, 'README.md'))
            front_dir = os.path.join(new_repo_dir, 'content', 'front')
            if not os.path.exists(front_dir):
                os.mkdir(front_dir)
                download_file('https://git.door43.org/api/v1/repos/unfoldingword/en_obs/raw/content/front/intro.md',
                              os.path.join(front_dir, 'intro.md'))
                download_file('https://git.door43.org/api/v1/repos/unfoldingword/en_obs/raw/content/front/title.md',
                            os.path.join(front_dir, 'title.md'))
            back_dir = os.path.join(new_repo_dir, 'content', 'back')
            if not os.path.exists(back_dir):
                os.mkdir(back_dir)
                download_file('https://git.door43.org/api/v1/repos/unfoldingword/en_obs/raw/content/back/intro.md',
                              os.path.join(new_repo_dir, 'content', 'back', 'intro.md'))
            self.repo_dir = new_repo_dir

    @property
    def tags(self):
        return sorted(self.repo.tags, key=lambda t: t.commit.committed_datetime)

    @property
    def latest_tag(self):
        tags = self.tags
        if tags and len(tags):
            return self.tags[-1].name

    @property
    def ref_is_tag(self):
        for tag in self.tags:
            if self.ref == tag.name:
                return True
        return False

    @property
    def commit(self):
        return self.repo.git.rev_parse('HEAD', short=10)

    @property
    def commit_date(self):
        return datetime.utcfromtimestamp(self.repo.head.commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def manifest(self):
        if not self._manifest and self.repo_dir:
            self._manifest = load_yaml_object(os.path.join(self.repo_dir, 'manifest.yaml'))
        return self._manifest

    @property
    def identifier(self):
        manifest_identifier = self.manifest['dublin_core']['identifier']
        if manifest_identifier and manifest_identifier.count('_'):
            return manifest_identifier.split('_')[1]
        else:
            return manifest_identifier

    @property
    def title(self):
        return self.manifest['dublin_core']['title']

    @property
    def language_name(self):
        return self.manifest['dublin_core']['language']['title']

    @property
    def language_title(self):
        return self.manifest['dublin_core']['language']['title']

    @property
    def language_id(self):
        return self.manifest['dublin_core']['language']['identifier']

    @property
    def language_direction(self):
        return self.manifest['dublin_core']['language']['direction']

    @property
    def simple_title(self):
        return self.title.replace('unfoldingWord® ', '')

    @property
    def type(self):
        return self.manifest['dublin_core']['type']

    @property
    def version(self):
        return self.manifest['dublin_core']['version']

    @property
    def publisher(self):
        return self.manifest['dublin_core']['publisher']

    @property
    def issued(self):
        return self.manifest['dublin_core']['issued']

    @property
    def contributors(self):
        return self.manifest['dublin_core']['contributor']

    @property
    def projects(self):
        return self.manifest['projects']

    def find_project(self, project_id):
        if self.projects:
            for project in self.projects:
                if project['identifier'] == project_id:
                    return project


class Resources(OrderedDict):
    @property
    def main(self) -> Resource:
        for key, value in self.items():
            return value
        else:
            raise IndexError("Empty ordered dict")
