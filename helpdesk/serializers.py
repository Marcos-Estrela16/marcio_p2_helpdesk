from rest_framework import serializers
from .models import Chamado, Categoria, Prioridade, Equipe

class EquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipe
        fields = ["id", "nome", "descricao", "email_contato", "ativa"]


class CategoriaSerializer(serializers.ModelSerializer):
    equipe_nome = serializers.ReadOnlyField(source="equipe.nome")

    class Meta:
        model = Categoria
        fields = ["id", "nome", "equipe", "equipe_nome", "descricao", "ativa"]

    def validate_equipe(self, value):
        user = self.context["request"].user
        if hasattr(user, "perfil") and value.organizacao != user.perfil.organizacao:
            raise serializers.ValidationError("A equipe selecionada pertence a outra organização.")
        return value


class PrioridadeSerializer(serializers.ModelSerializer):
    horas_sla = serializers.ReadOnlyField(source="sla.horas_resolucao")

    class Meta:
        model = Prioridade
        fields = ["id", "nivel", "nome", "peso", "cor_badge", "horas_sla"]


class ChamadoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.ReadOnlyField(source="categoria.nome")
    prioridade_nome = serializers.ReadOnlyField(source="prioridade.nome")
    dentro_do_prazo = serializers.ReadOnlyField()

    class Meta:
        model = Chamado
        fields = [
            "id",
            "protocolo",
            "titulo",
            "descricao",
            "solicitante_nome",
            "solicitante_email",
            "categoria",
            "categoria_nome",
            "prioridade",
            "prioridade_nome",
            "status",
            "data_abertura",
            "prazo_sla",
            "data_resolucao",
            "solucao",
            "dentro_do_prazo",
        ]
        read_only_fields = [
            "id",
            "protocolo",
            "data_abertura",
            "prazo_sla",
            "data_resolucao",
            "dentro_do_prazo",
        ]

    def validate_titulo(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("O título deve ter pelo menos 5 caracteres.")
        return value

    def validate_descricao(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("A descrição deve ter pelo menos 10 caracteres.")
        return value

    def validate_categoria(self, value):
        user = self.context["request"].user
        if hasattr(user, "perfil") and value.organizacao != user.perfil.organizacao:
            raise serializers.ValidationError("A categoria informada não pertence à sua organização.")
        return value
