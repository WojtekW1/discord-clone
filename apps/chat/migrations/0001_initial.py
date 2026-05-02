from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Channel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
                ("is_public", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_channels", to="accounts.user")),
            ],
            options={
                "permissions": [("can_manage_channels", "Can create/manage channels")],
            },
        ),
        migrations.CreateModel(
            name="DMConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("user1", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dm_user1", to="accounts.user")),
                ("user2", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dm_user2", to="accounts.user")),
            ],
        ),
        migrations.CreateModel(
            name="UserBan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(blank=True, default="", max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("banned_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bans_made", to="accounts.user")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bans", to="accounts.user")),
            ],
            options={
                "permissions": [("can_ban_user", "Can ban/unban users")],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(blank=True, default="")),
                ("image", models.ImageField(blank=True, null=True, upload_to="images/")),
                ("audio", models.FileField(blank=True, null=True, upload_to="audio/")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("is_deleted", models.BooleanField(default=False)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="accounts.user")),
                ("channel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.channel")),
                ("dm_conversation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.dmconversation")),
            ],
            options={
                "ordering": ["created_at"],
                "permissions": [("can_delete_any_message", "Can delete any message")],
            },
        ),
        migrations.CreateModel(
            name="ChannelMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("joined_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="chat.channel")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="channel_memberships", to="accounts.user")),
            ],
        ),
        migrations.AddConstraint(
            model_name="channelmembership",
            constraint=models.UniqueConstraint(fields=("channel", "user"), name="uniq_channel_member"),
        ),
        migrations.AddConstraint(
            model_name="dmconversation",
            constraint=models.UniqueConstraint(fields=("user1", "user2"), name="uniq_dm_pair"),
        ),
    ]
