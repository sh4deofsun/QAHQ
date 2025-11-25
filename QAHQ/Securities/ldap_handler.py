from ldap3 import Server, Connection, ALL, NTLM, SIMPLE
import os

# Configuration (should be loaded from env variables)
LDAP_SERVER_URL = os.getenv("LDAP_SERVER_URL", "ldap://localhost:389")
LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "cn=admin,dc=example,dc=com")
LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "admin")
LDAP_SEARCH_BASE = os.getenv("LDAP_SEARCH_BASE", "dc=example,dc=com")
LDAP_USE_SSL = os.getenv("LDAP_USE_SSL", "False").lower() == "true"

def verify_ldap_credentials(username, password):
    """
    Verifies credentials against the LDAP server.
    Returns True if valid, False otherwise.
    """
    try:
        server = Server(LDAP_SERVER_URL, get_info=ALL, use_ssl=LDAP_USE_SSL)
        # First bind with service account to search for user (if needed) or direct bind
        # For simplicity, assuming direct bind pattern or search-then-bind
        
        # Simple bind attempt with the provided credentials
        # Note: This assumes we know the user DN pattern or use a service account to find it.
        # Here we try to bind directly if we can construct the DN, or use a service account to search.
        
        # Strategy: Bind as admin, search for user, then try to bind as user.
        conn = Connection(server, user=LDAP_BIND_DN, password=LDAP_BIND_PASSWORD, auto_bind=True)
        
        search_filter = f"(uid={username})" # Adjust attribute as needed (sAMAccountName for AD)
        conn.search(LDAP_SEARCH_BASE, search_filter, attributes=['dn'])
        
        if not conn.entries:
            return False
            
        user_dn = conn.entries[0].entry_dn
        
        # Now try to bind as the user
        user_conn = Connection(server, user=user_dn, password=password)
        if user_conn.bind():
            user_conn.unbind()
            return True
        else:
            return False
            
    except Exception as e:
        print(f"LDAP Error: {e}")
        return False
