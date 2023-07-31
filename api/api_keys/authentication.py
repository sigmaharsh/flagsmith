from contextlib import suppress

from rest_framework import authentication, exceptions
from rest_framework_api_key.permissions import KeyParser

from api_keys.models import MasterAPIKey
from api_keys.user import APIKeyUser

key_parser = KeyParser()


class MasterAPIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        key = key_parser.get(request)

        if not key:
            return None

        with suppress(MasterAPIKey.DoesNotExist):
            if key := MasterAPIKey.objects.get_from_key(
                key
            ) and MasterAPIKey.objects.is_valid(key):
                return APIKeyUser(key), None

        raise exceptions.AuthenticationFailed("Valid Master API Key not found.")
