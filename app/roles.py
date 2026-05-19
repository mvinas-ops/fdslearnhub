ROLE_ADMIN = "Administrator"
ROLE_DEFAULT = "Default"
ROLE_BASIC = "Basic Account"
ROLE_FULL = "Full Account"

ROLE_CONFIG = {
    ROLE_ADMIN: {"access": True, "mask_pii": False},
    ROLE_DEFAULT: {"access": False, "mask_pii": True},
    ROLE_BASIC: {"access": True, "mask_pii": True},
    ROLE_FULL: {"access": True, "mask_pii": False},
}