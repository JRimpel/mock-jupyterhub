# Configuration file for jupyterhub.

c = get_config()  #noqa

c.JupyterHub.port = 8000
c.JupyterHub.base_url = '/jupyter/'
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'
c.JupyterHub.authenticator_class = 'xdmodauthenticator.XDMoDAuthenticator'
c.DockerSpawner.image = "xdmod-data:latest"
c.DockerSpawner.network_name = "jupyter-net"
c.JupyterHub.hub_connect_ip = 'jupyterhub'
c.DockerSpawner.environment = {
    'XDMOD_HOST': "https://xdmod:443/",
    'JUPYTERHUB_JWT_URL': "http://jwt-service:9888/",
    'CURL_CA_BUNDLE': "/etc/pki/tls/certs/xdmod.crt",
    'JUPYTERHUB_API_URL': 'http://jupyterhub:8081/jupyter/hub/api'
}

c.JupyterHub.services = [
    {
        'name': 'chart-service',
        'url': 'http://chart-service:2323/',
        'oauth_client_id': 'service-chart-service',
        'api_token': 'c780c3d34d334706b9988b5f5211d49d',
        'admin': True,
        'oauth_redirect_uri': '/jupyter/services/chart-service/oauth_callback/',
        'oauth_client_allowed_scopes':[
            'users',
            'servers',
            'access:servers!user'
        ]
    }
]

c.JupyterHub.load_roles = [
    {
        'name': 'user',
        'scopes': ['access:services', 'self']
    }
]

c.Authenticator.admin_users = {
    'admin',
    'admin1',
    'admin2'
}
