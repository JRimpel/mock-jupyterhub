from jose import jwt
import jose.exceptions
from jupyterhub.handlers import BaseHandler
from jupyterhub.auth import Authenticator


class XDMoDLoginHandler(BaseHandler):

    def get(self):
        url = self.get_next_url()
        redirect_url = '/rest/auth/jwt-redirect?next=' + url
        cookie = self.get_cookie('xdmod_jwt')
        if not cookie:
            self.redirect(redirect_url)
            return
        try:
            with open('/run/secrets/xdmod-public', 'r') as rsa_public_key_file:
                claims = jwt.decode(
                    cookie,
                    rsa_public_key_file.read(),
                    options={
                        'require_exp': True,
                        'require_sub': True,
                    },
                )
        except jose.exceptions.ExpiredSignatureError:
            self.redirect(redirect_url)
            return
        except (
            jose.exceptions.JWTError,
            jose.exceptions.JWTClaimsError
        ):
            self.send_error(401)
            return
        user = self.user_from_username(claims['sub'])
        self.set_login_cookie(user)
        self.redirect(url)


class XDMoDAuthenticator(Authenticator):

    def get_handlers(self, app):
        return [('/login', XDMoDLoginHandler)]
