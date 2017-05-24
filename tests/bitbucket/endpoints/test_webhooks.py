# -*- coding: utf-8 -*-
from __future__ import absolute_import

import six

from datetime import datetime
from django.utils import timezone
from sentry.models import Commit, CommitAuthor, OrganizationOption, Repository
from sentry.testutils import APITestCase
from uuid import uuid4

from sentry_plugins.bitbucket.testutils import PUSH_EVENT_EXAMPLE


class WebhookTest(APITestCase):
    def test_get(self):
        project = self.project  # force creation

        url = '/plugins/bitbucket/organizations/{}/webhook/'.format(
            project.organization.id,
        )

        response = self.client.get(url)

        assert response.status_code == 405

    def test_unregistered_event(self):
        project = self.project  # force creation
        url = '/plugins/bitbucket/organizations/{}/webhook/'.format(
            project.organization.id,
        )

        secret = 'b3002c3e321d4b7880360d397db2ccfd'

        OrganizationOption.objects.set_value(
            organization=project.organization,
            key='bitbucket:webhook_secret',
            value=secret,
        )

        response = self.client.post(
            path=url,
            data=PUSH_EVENT_EXAMPLE,
            content_type='application/json',
            HTTP_X_EVENT_KEY='UnregisteredEvent',
        )

        assert response.status_code == 204

    #     #todo(maxbittker) this isn't testable yet because the check isnt implemented
    # def test_invalid_signature_event(self):
    #     project = self.project  # force creation
    #
    #     url = '/plugins/bitbucket/organizations/{}/webhook/'.format(
    #         project.organization.id,
    #     )
    #
    #     secret = '2d7565c3537847b789d6995dca8d9f84'
    #     OrganizationOption.objects.set_value(
    #         organization=project.organization,
    #         key='bitbucket:webhook_secret',
    #         value=secret,
    #     )
    #
    #     response = self.client.post(
    #         path=url,
    #         data=PUSH_EVENT_EXAMPLE,
    #         content_type='application/json',
    #         HTTP_X_EVENT_KEY='repo:push',
    #     )
    #
    #     assert response.status_code == 401


class PushEventWebhookTest(APITestCase):
    def test_simple(self):
        project = self.project  # force creation

        url = '/plugins/bitbucket/organizations/{}/webhook/'.format(
            project.organization.id,
        )

        secret = 'b3002c3e321d4b7880360d397db2ccfd'

        OrganizationOption.objects.set_value(
            organization=project.organization,
            key='bitbucket:webhook_secret',
            value=secret,
        )

        Repository.objects.create(
            organization_id=project.organization.id,
            external_id='{c78dfb25-7882-4550-97b1-4e0d38f32859}',
            provider='bitbucket',
            name='maxbittker/newsdiffs',
        )

        response = self.client.post(
            path=url,
            data=PUSH_EVENT_EXAMPLE,
            content_type='application/json',
            HTTP_X_EVENT_KEY='repo:push',
        )

        assert response.status_code == 204

        commit_list = list(Commit.objects.filter(
            organization_id=project.organization_id,
        ).select_related('author').order_by('-date_added'))

        assert len(commit_list) == 1

        commit = commit_list[0]

        assert commit.key == 'e0e377d186e4f0e937bdb487a23384fe002df649'
        assert commit.message == u'README.md edited online with Bitbucket'
        assert commit.author.name == u'Max Bittker'
        assert commit.author.email == 'max@getsentry.com'
        assert commit.author.external_id is None
        assert commit.date_added == datetime(2017, 5, 24, 1, 5, 47, tzinfo=timezone.utc)


    def test_anonymous_lookup(self):
        project = self.project  # force creation

        url = '/plugins/bitbucket/organizations/{}/webhook/'.format(
            project.organization.id,
        )

        secret = 'b3002c3e321d4b7880360d397db2ccfd'

        OrganizationOption.objects.set_value(
            organization=project.organization,
            key='bitbucket:webhook_secret',
            value=secret,
        )

        Repository.objects.create(
            organization_id=project.organization.id,
            external_id='{c78dfb25-7882-4550-97b1-4e0d38f32859}',
            provider='bitbucket',
            name='maxbittker/newsdiffs',
        )

        CommitAuthor.objects.create(
            external_id='bitbucket:baxterthehacker',
            organization_id=project.organization_id,
            email='baxterthehacker@example.com',
            name=u'bàxterthehacker',
        )

        response = self.client.post(
            path=url,
            data=PUSH_EVENT_EXAMPLE,
            content_type='application/json',
            HTTP_X_EVENT_KEY='repo:push',
        )

        assert response.status_code == 204

        commit_list = list(Commit.objects.filter(
            organization_id=project.organization_id,
        ).select_related('author').order_by('-date_added'))

        # should be skipping the #skipsentry commit
        assert len(commit_list) == 1

        commit = commit_list[0]

        assert commit.key == 'e0e377d186e4f0e937bdb487a23384fe002df649'
        assert commit.message == u'README.md edited online with Bitbucket'
        assert commit.author.name == u'Max Bittker'
        assert commit.author.email == 'max@getsentry.com'
        assert commit.author.external_id is None
        assert commit.date_added == datetime(2017, 5, 24, 1, 5, 47, tzinfo=timezone.utc)
