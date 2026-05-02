from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import Profile
from apps.chat.models import Message, Channel, UserBan

User = get_user_model()

ROLE_ADMIN = "Administrator"
ROLE_MOD = "Moderator"
ROLE_USER = "User"

@receiver(post_save, sender=User)
def create_profile_and_default_group(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        # default group
        group, _ = Group.objects.get_or_create(name=ROLE_USER)
        instance.groups.add(group)

@receiver(post_migrate)
def ensure_roles(sender, **kwargs):
    # URUCHAMIAJ TYLKO po migracjach aplikacji chat (wtedy permissions już istnieją)
    if getattr(sender, "name", "") != "apps.chat":
        return

    admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
    mod_group, _ = Group.objects.get_or_create(name=ROLE_MOD)
    Group.objects.get_or_create(name=ROLE_USER)

    ct_msg = ContentType.objects.get_for_model(Message)
    ct_channel = ContentType.objects.get_for_model(Channel)
    ct_ban = ContentType.objects.get_for_model(UserBan)

    # Permissions mogą jeszcze nie istnieć przy pierwszym przebiegu -> zabezpieczenie
    try:
        perm_delete_msg = Permission.objects.get(content_type=ct_msg, codename="can_delete_any_message")
        perm_ban = Permission.objects.get(content_type=ct_ban, codename="can_ban_user")
        perm_manage_channels = Permission.objects.get(content_type=ct_channel, codename="can_manage_channels")
    except Permission.DoesNotExist:
        return

    mod_group.permissions.add(perm_delete_msg, perm_ban)
    admin_group.permissions.add(perm_delete_msg, perm_ban, perm_manage_channels)
