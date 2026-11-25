from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("helpdesk", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipe",
            name="organizacao",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)ss",
                to="core.organizacao",
                verbose_name="Organização",
            ),
        ),
        migrations.AddField(
            model_name="categoria",
            name="organizacao",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)ss",
                to="core.organizacao",
                verbose_name="Organização",
            ),
        ),
        migrations.AddField(
            model_name="chamado",
            name="organizacao",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)ss",
                to="core.organizacao",
                verbose_name="Organização",
            ),
        ),
    ]
