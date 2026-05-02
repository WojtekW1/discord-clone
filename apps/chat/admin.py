from django.contrib import admin
from .models import Channel, ChannelMembership, DMConversation, Message, UserBan, UserReport

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_public", "created_by", "created_at")
    search_fields = ("name",)

@admin.register(ChannelMembership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("channel", "user", "joined_at")
    search_fields = ("channel__name", "user__username")

@admin.register(DMConversation)
class DMAdmin(admin.ModelAdmin):
    list_display = ("id", "user1", "user2", "created_at")
    search_fields = ("user1__username", "user2__username")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "channel", "dm_conversation", "created_at", "is_deleted")
    search_fields = ("author__username", "text")

@admin.register(UserBan)
class BanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "banned_by", "is_active", "created_at")
    search_fields = ("user__username", "reason")

@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "reporter", "reported", "status", "reason")
    list_filter = ("status", "created_at")
    search_fields = ("reporter__username", "reported__username", "reason")
    ordering = ("-created_at",)