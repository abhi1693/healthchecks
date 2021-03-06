from hc.api.models import Channel, Check, Notification, Ping
from hc.test import BaseTestCase


class LogTestCase(BaseTestCase):

    def setUp(self):
        super(LogTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project)

        ping = Ping.objects.create(owner=self.check)

        # Older MySQL versions don't store microseconds. This makes sure
        # the ping is older than any notifications we may create later:
        ping.created = "2000-01-01T00:00:00+00:00"
        ping.save()

    def test_it_works(self):
        url = "/checks/%s/log/" % self.check.code

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertContains(r, "Local Time", status_code=200)

    def test_team_access_works(self):
        url = "/checks/%s/log/" % self.check.code

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/log/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/log/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_checks_ownership(self):
        url = "/checks/%s/log/" % self.check.code
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_pushover_notifications(self):
        ch = Channel.objects.create(kind="po", project=self.project)

        Notification(owner=self.check, channel=ch, check_status="down").save()

        url = "/checks/%s/log/" % self.check.code

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertContains(r, "Sent a Pushover notification", status_code=200)

    def test_it_shows_webhook_notifications(self):
        ch = Channel(kind="webhook", project=self.project)
        ch.value = "foo/$NAME"
        ch.save()

        Notification(owner=self.check, channel=ch, check_status="down").save()

        url = "/checks/%s/log/" % self.check.code

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertContains(r, "Called webhook foo/$NAME", status_code=200)

    def test_it_allows_cross_team_access(self):
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        url = "/checks/%s/log/" % self.check.code
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
