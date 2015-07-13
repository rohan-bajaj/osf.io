#!/usr/bin/env python
# encoding: utf-8

import mock
import unittest
import httpretty
from os.path import join as join_path
from json import dumps

from nose.tools import *  # noqa

import httplib as http

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from tests.test_addons import assert_urls_equal

from website.addons.figshare.tests.utils import create_mock_figshare
from website.addons.figshare import views
from website.addons.figshare import utils
from website.addons.figshare.views.config import serialize_settings
from website.util import api_url_for, web_url_for

from framework.auth import Auth

figshare_mock = create_mock_figshare(project=436)


class TestViewsConfig(OsfTestCase):

    def setUp(self):

        super(TestViewsConfig, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = self.user.auth
        self.project = ProjectFactory(creator=self.user)

        self.non_authenticator = AuthUserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.project.creator),
        )

        self.project.add_addon('figshare', auth=self.consolidated_auth)
        self.project.creator.add_addon('figshare')
        self.node_settings = self.project.get_addon('figshare')
        self.user_settings = self.project.creator.get_addon('figshare')
        self.user_settings.oauth_access_token = 'legittoken'
        self.user_settings.oauth_access_token_secret = 'legittoken'
        self.user_settings.save()
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '123456'
        self.node_settings.figshare_type = 'project'
        self.node_settings.figshare_title = 'FIGSHARE_TITLE'
        self.node_settings.save()

        self.figshare = create_mock_figshare('test')

    def configure_responses(self):
        httpretty.register_uri(
            httpretty.GET,
            join_path(self.node_settings.api_url, 'articles'),
            body=dumps(self.figshare.articles.return_value)
        )
        httpretty.register_uri(
            httpretty.GET,
            join_path(self.node_settings.api_url, 'articles', '902210'),
            body=dumps(self.figshare.article.return_value)
        )

    @httpretty.activate
    def test_import_auth(self):
        self.configure_responses()
        """Testing figshare_import_user_auth to ensure that auth gets imported correctly"""
        settings = self.node_settings
        settings.user_settings = None
        settings.save()
        url = '/api/v1/project/{0}/figshare/config/import-auth/'.format(self.project._id)
        self.app.put(url, auth=self.user.auth)
        self.node_settings.reload()
        assert_is_not_none(settings.user_settings)

    def test_cancelled_oauth_request_from_user_settings_page_redirects_correctly(self):
        res = self.app.get(api_url_for('figshare_oauth_callback', uid=self.user._id), auth=self.user.auth)
        assert_equal(res.status_code, 302)
        assert_urls_equal(res.headers['location'], web_url_for('user_addons'))

    def test_cancelled_oauth_request_from_node_settings_page_redirects_correctly(self):
        res = self.app.get(api_url_for('figshare_oauth_callback', uid=self.user._id, nid=self.project._id), auth=self.user.auth)
        assert_equal(res.status_code, 302)
        assert_urls_equal(res.headers['location'], self.project.web_url_for('node_setting'))

    def test_deauthorize(self):
        """Testing figshare_deauthorize to ensure user auth gets removed from
        the node and that the AddonNodeSettings are cleared

        """
        settings = self.node_settings
        url = '/api/v1/project/{0}/figshare/config/'.format(self.project._id)
        self.app.delete(url, auth=self.user.auth)
        self.node_settings.reload()
        assert_true(settings.user_settings is None)
        is_none = (
            settings.figshare_id is None and settings.figshare_title is None and settings.figshare_type is None
        )
        assert_true(is_none)

    def test_config_no_change(self):
        nlogs = len(self.project.logs)
        url = self.project.api_url_for('figshare_config_put')
        rv = self.app.put_json(
            url,
            {
                'selected': {
                    'id': '123456',
                    'name': 'FIGSHARE_TITLE',
                    'type': 'project',
                },
            },
            auth=self.user.auth,
        )
        self.project.reload()
        assert_equal(rv.status_int, http.OK)
        assert_equal(len(self.project.logs), nlogs)

    def test_config_change(self):
        nlogs = len(self.project.logs)
        url = self.project.api_url_for('figshare_config_put')
        rv = self.app.put_json(
            url,
            {
                'selected': {
                    'id': 'project_9001',
                    'name': 'IchangedbecauseIcan',
                    'type': 'project'
                },
            },
            auth=self.user.auth,
        )
        self.project.reload()
        self.node_settings.reload()

        assert_equal(rv.status_int, http.OK)
        assert_equal(self.node_settings.figshare_id, 'project_9001')
        assert_equal(self.node_settings.figshare_title, 'IchangedbecauseIcan')
        assert_equal(len(self.project.logs), nlogs + 1)
        assert_equal(
            self.project.logs[nlogs].action,
            'figshare_content_linked'
        )

    def test_config_change_invalid(self):
        nlogs = len(self.project.logs)
        url = self.project.api_url_for('figshare_config_put')
        rv = self.app.put_json(
            url,
            {
                'selected': {
                    'type': 'project'
                },
            },
            auth=self.user.auth,
            expect_errors=True,
        )
        self.project.reload()
        self.node_settings.reload()

        assert_equal(rv.status_int, http.BAD_REQUEST)
        assert_equal(len(self.project.logs), nlogs)

    def test_config_change_not_owner(self):
        user2 = AuthUserFactory()
        self.project.add_contributor(user2, save=True)
        nlogs = len(self.project.logs)
        url = self.project.api_url_for('figshare_config_put')
        res = self.app.put_json(
            url,
            {},
            auth=user2.auth,
            expect_errors=True,
        )
        self.project.reload()
        assert_equal(res.status_int, http.FORBIDDEN)
        assert_equal(nlogs, len(self.project.logs))

    @httpretty.activate
    def test_serialize_settings_helper_returns_correct_auth_info(self):
        self.configure_responses()

        result = serialize_settings(self.node_settings, self.user, client=figshare_mock)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    @httpretty.activate
    def test_serialize_settings_for_user_no_auth(self):
        self.configure_responses()

        no_addon_user = AuthUserFactory()
        result = serialize_settings(self.node_settings, no_addon_user, client=figshare_mock)
        assert_false(result['userIsOwner'])
        assert_false(result['userHasAuth'])


class TestUtils(OsfTestCase):

    def setUp(self):

        super(TestUtils, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = self.user.auth
        self.project = ProjectFactory(creator=self.user)

        self.non_authenticator = AuthUserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.project.creator),
        )

        self.project.add_addon('figshare', auth=self.consolidated_auth)
        self.project.creator.add_addon('figshare')
        self.node_settings = self.project.get_addon('figshare')
        self.user_settings = self.project.creator.get_addon('figshare')
        self.user_settings.oauth_access_token = 'legittoken'
        self.user_settings.oauth_access_token_secret = 'legittoken'
        self.user_settings.save()
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '436'
        self.node_settings.figshare_type = 'project'
        self.node_settings.save()

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_project_to_hgrid(self, *args, **kwargs):
        project = figshare_mock.project.return_value
        hgrid = utils.project_to_hgrid(self.project, project, self.user, True)

        assert_equals(len(hgrid), len(project['articles']))
        folders_in_project = len(
            [a for a in project.get('articles') or [] if a['defined_type'] == 'fileset'])
        folders_in_hgrid = len([h for h in hgrid if type(h) is list])

        assert_equals(folders_in_project, folders_in_hgrid)
        files_in_project = 0
        files_in_hgrid = 0
        for a in project.get('articles') or []:
            if a['defined_type'] == 'fileset':
                files_in_project = files_in_project + len(a['files'])
            else:
                files_in_project = files_in_project + 1

        for a in hgrid:
            if type(a) is list:
                assert_equals(a[0]['kind'], 'file')
                files_in_hgrid = files_in_hgrid + len(a)
            else:
                assert_equals(a['kind'], 'file')
                files_in_hgrid = files_in_hgrid + 1

        assert_equals(files_in_hgrid, files_in_project)

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_project_to_hgrid_no_auth(self, project):
        project.return_value = 'notNone'
        self.node_settings.user_settings = None
        ref = views.hgrid.figshare_hgrid_data(self.node_settings, self.auth)
        assert_equal(ref, None)

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_project_to_hgrid_no_id(self, project):
        project.return_value = 'not none'
        self.node_settings.figshare_id = None
        ref = views.hgrid.figshare_hgrid_data(self.node_settings, self.auth)
        assert_equal(ref, None)

    @mock.patch('website.addons.figshare.api.Figshare.project')
    def test_hgrid_deleted_project(self, project):
        project.return_value = None
        ref = views.hgrid.figshare_hgrid_data(self.node_settings, self.auth)
        assert_equal(ref, None)


class TestViewsAuth(OsfTestCase):

    def setUp(self):

        super(TestViewsAuth, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = self.user.auth
        self.project = ProjectFactory(creator=self.user)

        self.non_authenticator = AuthUserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.project.creator),
        )

        self.project.add_addon('figshare', auth=self.consolidated_auth)
        self.project.creator.add_addon('figshare')
        self.node_settings = self.project.get_addon('figshare')
        self.user_settings = self.project.creator.get_addon('figshare')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '436'
        self.node_settings.figshare_type = 'project'
        self.node_settings.save()

    @unittest.skip('finish this')
    def test_oauth_fail(self):
        url = '/api/v1/project/{0}/figshare/oauth/'.format(self.project._id)
        self.app.get(url, auth=self.user.auth)

    @unittest.skip('finish this')
    def test_oauth_bad_token(self):
        pass
