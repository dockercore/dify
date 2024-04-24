import logging

from libs.passport import PassportService
from services.enterprise.base import EnterpriseRequest

logger = logging.getLogger(__name__)


class EnterpriseWebSSOService:

    @classmethod
    def get_sso_saml_login(cls) -> str:
        return EnterpriseRequest.send_request('GET', '/sso/web/saml/login')

    @classmethod
    def post_sso_saml_acs(cls, saml_response: str) -> str:
        response = EnterpriseRequest.send_request('POST', '/sso/web/saml/acs', json={'SAMLResponse': saml_response})
        if 'email' not in response or response['email'] is None or response['email'] == '':
            logger.exception(response)
            raise Exception('email not found in SAML response: ' + response)

        return cls.generate_web_sso_token(response.get('email'))

    @classmethod
    def get_sso_oidc_login(cls):
        return EnterpriseRequest.send_request('GET', '/sso/web/oidc/login')

    @classmethod
    def get_sso_oidc_callback(cls, args: dict):
        code_from_query = args['code']

        response = EnterpriseRequest.send_request('GET', '/sso/web/oidc/callback', params={'code': code_from_query})
        if 'email' not in response or response['email'] is None or response['email'] == '':
            logger.exception(response)
            raise Exception('email not found in OIDC response: ' + response)

        return cls.generate_web_sso_token(response.get('email'))

    @classmethod
    def generate_web_sso_token(cls, end_user_session_id: str) -> str:
        payload = {
            'end_user_session_id': end_user_session_id,
        }

        token = PassportService().issue(payload)

        return token
