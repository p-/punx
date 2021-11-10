#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     prjemian@gmail.com
# :copyright: (c) 2016, Pete R. Jemian
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------

"""
manages the communications with GitHub


.. autosummary::

    ~GitHub_Repository_Reference

USAGE::

    grr = punx.github_handler.GitHub_Repository_Reference()
    grr.connect_repo()
    if grr.request_info(u'v3.2') is not None:
        d = grr.download()

"""


import datetime
import github
import os
import requests
import warnings

from requests.packages.urllib3 import disable_warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from . import utils


logger = utils.setup_logger(__name__)

DEFAULT_BRANCH_NAME = "main"
DEFAULT_RELEASE_NAME = "v2018.5"
# DEFAULT_TAG_NAME = u'NXroot-1.0'
DEFAULT_TAG_NAME = "Schema-3.3"
DEFAULT_COMMIT_NAME = "a4fd52d"
DEFAULT_NXDL_SET = DEFAULT_RELEASE_NAME
GITHUB_RETRY_COUNT = 3

GITHUB_NXDL_ORGANIZATION = "nexusformat"
GITHUB_NXDL_REPOSITORY = "definitions"
GITHUB_NXDL_BRANCH = "master"
GITHUB_RETRY_COUNT = 3
# NXDL_CACHE_SUBDIR = GITHUB_NXDL_REPOSITORY + '-' + GITHUB_NXDL_BRANCH


def get_GitHub_credentials():
    """
    Get the Github API token from a file or environment.

    GitHub requests use an access token. The token is unique to a user and may
    be generated by visiting https://github.com/settings/tokens.

    The token is provided in either of these environment variables: ``GH_TOKEN``
    or ``GITHUB_TOKEN`` (searched in that order).

    Issues a warning and returns ``None`` if credentials are not found per above
    search.
    """
    # check for environment variables
    for variable in ["GH_TOKEN", "GITHUB_TOKEN"]:
        token = os.environ.get(variable)
        if token is not None:
            return token

    warnings.warn(
        "Did not find environment variables GH_TOKEN or GITHUB_TOKEN",
        UserWarning,
    )
    # TODO: move next conent to documentation.
    # warnings.warn(
    #     "Did not find environment variables GH_TOKEN or GITHUB_TOKEN"
    #     " which provide the GitHub API token necessary to download"
    #     " resources from GitHub through its API.  You may experience"
    #     " restrictions on the amount of content that can be downloaded"
    #     " over a chort intervale (such as an hour or so)."
    # )
    return None


class GitHub_Repository_Reference(object):

    """
    all information necessary to describe and download a repository branch, release, tag, or SHA hash

    ROUTINES

    .. autosummary::

        ~connect_repo
        ~request_info
        ~download

    :see: https://github.com/PyGithub/PyGithub/tree/master/github
    """

    def __init__(self):
        self.orgName = GITHUB_NXDL_ORGANIZATION
        self.appName = GITHUB_NXDL_REPOSITORY
        self.repo = None
        self.ref = None
        self.ref_type = None
        self.sha = None
        self.zip_url = None
        self.last_modified = None

    def connect_repo(self, repo_name=None, token=None):
        """
        connect with the GitHub repository

        :param str repo_name: name of repository in https://github.com/nexusformat (default: *definitions*)
        :param str or None token: GitHub access token or ``None``
        :returns bool: True if using GitHub credentials
        """
        repo_name = repo_name or self.appName

        token = get_GitHub_credentials() if token is None else token

        # also set the repo attribute
        gh = github.Github(token)  # token is either None or a str
        user = gh.get_user(self.orgName)
        self.repo = user.get_repo(repo_name)

        return isinstance(token, str)

    def request_info(self, ref=None):
        """
        request download information about ``ref``

        :param str ref: name of branch, release, tag, or SHA hash (default: *v3.2*)

        download URLs

        * base:  https://github.com
        * master: https://github.com/nexusformat/definitions/archive/master.zip
        * branch (www_page_486): https://github.com/nexusformat/definitions/archive/www_page_486.zip
        * hash (83ce630): https://github.com/nexusformat/definitions/archive/83ce630.zip
        * release (v3.2): see hash c0b9500
        * tag (NXcanSAS-1.0): see hash 83ce630
        """
        ref = ref or DEFAULT_NXDL_SET
        if self.repo is None:
            raise ValueError("call connect_repo() first")

        node = (
            self.get_branch(ref)
            or self.get_release(ref)
            or self.get_tag(ref)
            or self.get_commit(ref)
        )
        return node

    def download(self):
        """
        download the NXDL definitions described by ``ref``
        """
        # "disabling warnings about GitHub self-signed https certificates"
        disable_warnings(InsecureRequestWarning)

        token = get_GitHub_credentials()
        content = None
        for _retry in range(GITHUB_RETRY_COUNT):  # noqa
            try:
                if token is None:
                    content = requests.get(self.zip_url, verify=False)
                else:
                    content = requests.get(
                        self.zip_url,
                        headers={"Authorization": f"TOK:{token}"},
                        verify=False,
                    )
            except requests.exceptions.ConnectionError as _exc:
                raise IOError("ConnectionError from " + self.zip_url + "\n" + str(_exc))
            else:
                break

        return content

    def _make_zip_url(self, ref=DEFAULT_BRANCH_NAME):
        """create the download URL for the ``ref``"""
        url = "https://github.com/"
        url += "/".join([self.orgName, self.appName, "archive", ref])
        url += ".zip"
        return url

    def _get_last_modified(self):
        """get the ``last_modified`` date from the SHA's commit"""
        if self.sha is not None:
            commit = self.repo.get_commit(self.sha)
            mod_date_time = commit.last_modified  # Tue, 20 Dec 2016 18:30:29 GMT
            fmt = "%a, %d %b %Y %H:%M:%S %Z"  # --> 2016-11-19 01:04:28
            mod_date_time = datetime.datetime.strptime(commit.last_modified, fmt)
            self.last_modified = str(mod_date_time)

    def get_branch(self, ref=DEFAULT_BRANCH_NAME):
        """
        learn the download information about the named branch

        :param str ref: name of branch in repository
        """
        try:
            node = self.repo.get_branch(ref)
            self.ref = ref
            self.ref_type = "branch"
            self.sha = node.commit.sha
            self.zip_url = self._make_zip_url(self.sha[:7])
            self._get_last_modified()
            return node
        except github.GithubException:
            return None

    def get_release(self, ref=DEFAULT_RELEASE_NAME):
        """
        learn the download information about the named release

        :param str ref: name of release in repository
        """
        try:
            node = self.repo.get_release(ref)
            self.get_tag(node.tag_name)
            self.ref = ref
            self.ref_type = "release"
            return node
        except github.GithubException:
            return None

    def get_tag(self, ref=DEFAULT_TAG_NAME):
        """
        learn the download information about the named tag

        :param str ref: name of tag in repository
        """
        try:
            for tag in self.repo.get_tags():
                if tag.name == ref:
                    self.ref = ref
                    self.ref_type = "tag"
                    self.sha = tag.commit.sha
                    # self.zip_url = self._make_zip_url(self.sha[:7])
                    self.zip_url = tag.zipball_url
                    self._get_last_modified()
                    return tag
        except github.GithubException:
            return None

    def get_commit(self, ref=DEFAULT_COMMIT_NAME):
        """
        learn the download information about the referenced commit

        :param str ref: name of SHA hash, first unique characters are sufficient, usually 7 or less
        """
        try:
            node = self.repo.get_commit(ref)
            self.ref = ref
            self.ref_type = "commit"
            self.sha = node.commit.sha
            self.zip_url = self._make_zip_url(self.sha[:7])
            self._get_last_modified()
            return node
        except github.GithubException:
            return None
