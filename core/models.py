from django.db import models
from django.contrib.auth.models import User

class Organizacao(models.Model):
    nome = models.CharField(max_length=120, unique=True, verbose_name="Nome da Organização")
    criada_em = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    class Meta:
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class DaOrganizacao(models.Model):
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.PROTECT,
        verbose_name="Organização",
        related_name="%(app_label)s_%(class)ss",
    )

    class Meta:
        abstract = True


class Perfil(models.Model):
    PAPEL_CHOICES = [
        ("admin", "Administrador"),
        ("operador", "Operador"),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="Usuário",
    )
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.PROTECT,
        related_name="perfis",
        verbose_name="Organização",
    )
    papel = models.CharField(
        max_length=20,
        choices=PAPEL_CHOICES,
        default="operador",
        verbose_name="Papel de Acesso",
    )

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"

    def __str__(self):
        return f"{self.usuario.username} ({self.organizacao.nome} - {self.get_papel_display()})"
