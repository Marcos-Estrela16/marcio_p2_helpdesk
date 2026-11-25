from django.db import migrations

def org_padrao(apps, schema_editor):
    Organizacao = apps.get_model("core", "Organizacao")
    Equipe = apps.get_model("helpdesk", "Equipe")
    Categoria = apps.get_model("helpdesk", "Categoria")
    Chamado = apps.get_model("helpdesk", "Chamado")

    org, _ = Organizacao.objects.get_or_create(nome="Organização Padrão")

    Equipe.objects.filter(organizacao__isnull=True).update(organizacao=org)
    Categoria.objects.filter(organizacao__isnull=True).update(organizacao=org)
    Chamado.objects.filter(organizacao__isnull=True).update(organizacao=org)

class Migration(migrations.Migration):

    dependencies = [
        ("helpdesk", "0002_add_org_fields"),
    ]

    operations = [
        migrations.RunPython(org_padrao, reverse_code=migrations.RunPython.noop),
    ]
