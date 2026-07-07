import logging

from ..core.config import settings

log = logging.getLogger(__name__)


def verify_ldap_credentials(username: str, password: str) -> bool:
    """Search-then-bind. Returns False when LDAP is not configured."""
    if not settings.ldap_server_url or not password:
        return False
    try:
        from ldap3 import ALL, Connection, Server

        server = Server(settings.ldap_server_url, get_info=ALL, use_ssl=settings.ldap_use_ssl)
        conn = Connection(
            server,
            user=settings.ldap_bind_dn,
            password=settings.ldap_bind_password,
            auto_bind=True,
        )
        conn.search(
            settings.ldap_search_base,
            settings.ldap_user_filter.format(username=username),
            attributes=[],
        )
        if not conn.entries:
            return False
        user_dn = conn.entries[0].entry_dn
        conn.unbind()

        user_conn = Connection(server, user=user_dn, password=password)
        if user_conn.bind():
            user_conn.unbind()
            return True
        return False
    except Exception as e:
        log.warning("LDAP error: %s", e)
        return False
