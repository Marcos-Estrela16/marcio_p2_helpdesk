from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("helpdesk", "0003_dados_org"),
    ]

    operations = [
        migrations.AlterField(
            model_name="equipe",
            name="organizacao",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)ss",
                to="core.organizacao",
                verbose_name="Organização",
            ),
        ),
        migrations.AlterField(
            model_name="categoria",
            name="organizacao",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)ss",
                to="core.organizacao",
                verbose_name="Organização",
            ),
        ),
        migrations.AlterField(
            model_name="chamado",
            name="organizacao",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)ss",
                to="core.organizacao",
                verbose_name="Organização",
            ),
        ),
        migrations.AlterField(
            model_name="chamado",
            name="protocolo",
            field=models.CharField(max_length=30, verbose_name="Protocolo"),
        ),
        migrations.AddConstraint(
            model_name="equipe",
            constraint=models.UniqueConstraint(
                fields=("organizacao", "nome"),
                name="equipe_nome_unica_por_org",
            ),
        ),
        migrations.AddConstraint(
            model_name="categoria",
            constraint=models.UniqueConstraint(
                fields=("organizacao", "nome"),
                name="categoria_nome_unica_por_org",
            ),
        ),
        migrations.AddConstraint(
            model_name="chamado",
            constraint=models.UniqueConstraint(
                fields=("organizacao", "protocolo"),
                name="chamado_protocolo_unico_por_org",
            ),
        ),
        migrations.AddIndex(
            model_name="chamado",
            index=models.Index(fields=["data_abertura"], name="helpdesk_ch_data_ab_idx"),
        ),
        migrations.AddIndex(
            model_name="chamado",
            index=models.Index(fields=["status"], name="helpdesk_ch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="chamado",
            index=models.Index(fields=["organizacao", "status"], name="helpdesk_ch_org_stat_idx"),
        ),
    ]
