from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.urls import reverse
from django.core import cache
from .settings import gsheets_settings
from .models import AccessCredentials
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery


class AuthorizeView(TemplateView):
    def get(self, request, *args, **kwargs):
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            gsheets_settings.CLIENT_SECRETS, scopes=gsheets_settings.SCOPES
        )

        # The URI created here must exactly match one of the authorized redirect URIs
        # for the OAuth 2.0 client, which you configured in the API Console. If this
        # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
        # error.
        flow.redirect_uri = request.build_absolute_uri(reverse('gsheets_auth_success'))

        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true'
        )

        # Store the state so the callback can verify the auth server response.
        request.session['state'] = state

        return redirect(authorization_url)


class OAuthSuccessView(TemplateView):
    def get(self, request, *args, **kwargs):
        # Specify the state when creating the flow in the callback so that it can
        # verified in the authorization server response.
        state = request.session['state']

        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            gsheets_settings.CLIENT_SECRETS, scopes=gsheets_settings.SCOPES, state=state
        )
        flow.redirect_uri = request.build_absolute_uri(reverse('gsheets_auth_success'))

        # Use the authorization server's response to fetch the OAuth 2.0 tokens.
        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)

        # Store credentials in the session.
        # ACTION ITEM: In a production app, you likely want to save these
        #              credentials in a persistent database instead.
        credentials = flow.credentials
        ac, created = AccessCredentials.objects.get_or_create(token=credentials.token, defaults={
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
        })

        # redirect to admin page for the AC
        return redirect(reverse('admin:access_credentials_change', args=(ac.id,)))