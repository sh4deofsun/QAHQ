## 2024-05-24 - Hardcoded Secret Key
**Vulnerability:** A hardcoded default `SECRET_KEY` was found in the authentication module, which serves as a fallback when the environment variable is missing. This allows attackers to forge authentication tokens if the deployment does not explicitly set a secret key.
**Learning:** Hardcoded fallbacks for sensitive secrets, even if intended for development, create a high risk of insecure defaults in production. Developers may forget to set the environment variable, leaving the application vulnerable.
**Prevention:** Remove hardcoded defaults for critical secrets. Instead, enforce the presence of the environment variable or generate a secure random value at runtime (with a warning) to fail safely or operate securely but transiently.
