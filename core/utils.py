from .models import Organizacao, Perfil

def org_atual(request):
    """
    Retorna a organização associada ao usuário autenticado atual.
    Caso o usuário seja superusuário e ainda não possua perfil,
    vincula-o a uma organização padrão para evitar quebras de sistema.
    """
    if not request.user.is_authenticated:
        return None
    try:
        return request.user.perfil.organizacao
    except (AttributeError, Perfil.DoesNotExist):
        if request.user.is_superuser:
            org, _ = Organizacao.objects.get_or_create(nome="Organização Padrão")
            perfil, _ = Perfil.objects.get_or_create(
                usuario=request.user,
                defaults={"organizacao": org, "papel": "admin"}
            )
            return perfil.organizacao
        return None
