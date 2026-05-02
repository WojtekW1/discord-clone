def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name="Administrator").exists())

def is_moderator(user):
    return user.is_authenticated and (is_admin(user) or user.groups.filter(name="Moderator").exists())

def can_manage_channels(user):
    return user.is_authenticated and (is_admin(user) or user.has_perm("chat.can_manage_channels"))

def can_delete_any_message(user):
    return user.is_authenticated and (is_moderator(user) or user.has_perm("chat.can_delete_any_message"))

def can_ban_user(user):
    return user.is_authenticated and (is_moderator(user) or user.has_perm("chat.can_ban_user"))
