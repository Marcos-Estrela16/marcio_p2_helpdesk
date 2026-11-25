from django.test import TestCase, Client
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import Organizacao, Perfil
from .models import Equipe, Prioridade, SLA, Categoria, Chamado
from .forms import ChamadoForm, ResolverChamadoForm, PeriodoForm


class HelpDeskP1Testes(TestCase):
    def setUp(self):
        self.client = Client()
        self.org_a = Organizacao.objects.create(nome="Empresa Alfa")
        self.user_a = User.objects.create_user(username="usuario_a", password="password123")
        self.perfil_a = Perfil.objects.create(usuario=self.user_a, organizacao=self.org_a, papel="operador")
        self.client.force_login(self.user_a)

        self.equipe = Equipe.objects.create(
            nome="NOC Redes",
            email_contato="noc@empresa.com",
            ativa=True,
            organizacao=self.org_a,
        )
        self.prioridade = Prioridade.objects.create(
            nivel="alta",
            nome="Alta Severidade",
            peso=2,
            cor_badge="warning",
        )
        self.sla = SLA.objects.create(
            prioridade=self.prioridade,
            horas_resolucao=12,
            descricao="SLA de 12 horas",
        )
        self.categoria = Categoria.objects.create(
            nome="Falha de Roteamento",
            equipe=self.equipe,
            ativa=True,
            organizacao=self.org_a,
        )

    def test_todas_as_entidades_existem(self):
        self.assertEqual(Equipe.objects.count(), 1)
        self.assertEqual(Prioridade.objects.count(), 1)
        self.assertEqual(SLA.objects.count(), 1)
        self.assertEqual(Categoria.objects.count(), 1)

    def test_rotas_principais_http_200(self):
        self.assertEqual(self.client.get(reverse("index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("slas_info")).status_code, 200)
        self.assertEqual(self.client.get(reverse("novo_chamado")).status_code, 200)

    def test_calculo_automatico_sla_e_resolucao(self):
        # 1. Abertura do Chamado via POST
        res = self.client.post(reverse("novo_chamado"), {
            "titulo": "Link de Internet Caiu",
            "categoria": self.categoria.id,
            "prioridade": self.prioridade.id,
            "solicitante_nome": "Marcos Estrela",
            "solicitante_email": "marcos@empresa.com",
            "descricao": "Roteador principal sem sincronismo óptico.",
        })
        self.assertEqual(res.status_code, 302)

        chamado = Chamado.objects.get(titulo="Link de Internet Caiu")
        self.assertIsNotNone(chamado.protocolo)
        self.assertIsNotNone(chamado.prazo_sla)
        self.assertEqual(chamado.organizacao, self.org_a)

        # Validação: o prazo de SLA deve ser aproximadamente data_abertura + 12 horas
        diferenca_horas = (chamado.prazo_sla - chamado.data_abertura).total_seconds() / 3600
        self.assertAlmostEqual(diferenca_horas, 12, delta=0.1)
        self.assertTrue(chamado.dentro_do_prazo)

        # 2. Resolução do Chamado
        res_resolver = self.client.post(reverse("detalhes_chamado", args=[chamado.id]), {
            "status": "resolvido",
            "solucao": "Reinicializada a porta do switch e reconfigurado BGP.",
        })
        self.assertEqual(res_resolver.status_code, 302)

        chamado.refresh_from_db()
        self.assertEqual(chamado.status, "resolvido")
        self.assertIsNotNone(chamado.data_resolucao)
        self.assertTrue(chamado.dentro_do_prazo)

    def test_feature1_busca_e_filtros_combinados_com_q(self):
        p_critica = Prioridade.objects.create(nivel="critica", nome="Crítica Urgente", peso=1, cor_badge="danger")
        SLA.objects.create(prioridade=p_critica, horas_resolucao=4, descricao="SLA 4h")
        cat_bd = Categoria.objects.create(nome="Banco Postgres", equipe=self.equipe, ativa=True, organizacao=self.org_a)

        c1 = Chamado.objects.create(
            titulo="Servidor de Produção Down",
            descricao="Nenhum usuário consegue acessar o sistema ERP.",
            solicitante_nome="Carlos Silva",
            solicitante_email="carlos@empresa.com",
            categoria=self.categoria,
            prioridade=self.prioridade,
            status="aberto",
            organizacao=self.org_a,
        )
        c2 = Chamado.objects.create(
            titulo="Lentidão na Consulta SQL",
            descricao="Queries no Postgres estão levando mais de 10 segundos.",
            solicitante_nome="Ana Lima",
            solicitante_email="ana@empresa.com",
            categoria=cat_bd,
            prioridade=p_critica,
            status="resolvido",
            organizacao=self.org_a,
        )

        # 1. Busca por texto (q) no título
        res_busca = self.client.get(reverse("index") + "?q=produção")
        self.assertContains(res_busca, "Servidor de Produção Down")
        self.assertNotContains(res_busca, "Lentidão na Consulta SQL")

        # 2. Busca por texto (q) na descrição
        res_busca_desc = self.client.get(reverse("index") + "?q=Postgres")
        self.assertContains(res_busca_desc, "Lentidão na Consulta SQL")
        self.assertNotContains(res_busca_desc, "Servidor de Produção Down")

        # 3. Filtro por status
        res_status = self.client.get(reverse("index") + "?status=resolvido")
        self.assertContains(res_status, "Lentidão na Consulta SQL")
        self.assertNotContains(res_status, "Servidor de Produção Down")

        # 4. Busca por texto E filtro por categoria combinados com Q()
        res_combinado = self.client.get(reverse("index") + f"?q=Lentidão&categoria={cat_bd.id}&status=resolvido")
        self.assertContains(res_combinado, "Lentidão na Consulta SQL")
        self.assertNotContains(res_combinado, "Servidor de Produção Down")

        # 5. Resultado vazio exibe mensagem clara ({% empty %})
        res_vazio = self.client.get(reverse("index") + "?q=TextoInexistenteXYZ")
        self.assertContains(res_vazio, "Nenhum chamado encontrado")

    def test_feature2_validacao_customizada_sla_e_prioridade_critica(self):
        # 1. Validação de título muito curto
        form_curto = ChamadoForm(org=self.org_a, data={
            "titulo": "Bug",
            "categoria": self.categoria.id,
            "prioridade": self.prioridade.id,
            "solicitante_nome": "Marcos",
            "solicitante_email": "marcos@empresa.com",
            "descricao": "Descrição válida do problema no servidor.",
        })
        self.assertFalse(form_curto.is_valid())
        self.assertIn("titulo", form_curto.errors)
        self.assertIn("pelo menos 5 caracteres", form_curto.errors["titulo"][0])

        # 2. Validação de título vago (termo genérico)
        form_vago = ChamadoForm(org=self.org_a, data={
            "titulo": "teste",
            "categoria": self.categoria.id,
            "prioridade": self.prioridade.id,
            "solicitante_nome": "Marcos",
            "solicitante_email": "marcos@empresa.com",
            "descricao": "Descrição válida do problema no servidor.",
        })
        self.assertFalse(form_vago.is_valid())
        self.assertIn("titulo", form_vago.errors)
        self.assertIn("muito vago", form_vago.errors["titulo"][0])

        # 3. Validação de Chamado com prioridade Crítica sem detalhamento suficiente (< 30 chars)
        p_critica = Prioridade.objects.create(nivel="critica", nome="Crítica", peso=1)
        SLA.objects.create(prioridade=p_critica, horas_resolucao=2, descricao="SLA 2h")
        form_critica_curta = ChamadoForm(org=self.org_a, data={
            "titulo": "Parada do Gateway",
            "categoria": self.categoria.id,
            "prioridade": p_critica.id,
            "solicitante_nome": "Marcos",
            "solicitante_email": "marcos@empresa.com",
            "descricao": "Caiu tudo.",
        })
        self.assertFalse(form_critica_curta.is_valid())
        self.assertIn("descricao", form_critica_curta.errors)
        self.assertIn("30 caracteres", form_critica_curta.errors["descricao"][0])

        # 4. Validação da rubrica do professor: Prazo do SLA não pode ser anterior/igual à abertura
        p_invalida = Prioridade.objects.create(nivel="baixa", nome="Sem SLA", peso=4)
        SLA.objects.create(prioridade=p_invalida, horas_resolucao=0, descricao="SLA zero")
        form_sla_invalido = ChamadoForm(org=self.org_a, data={
            "titulo": "Dúvida de Procedimento",
            "categoria": self.categoria.id,
            "prioridade": p_invalida.id,
            "solicitante_nome": "Marcos",
            "solicitante_email": "marcos@empresa.com",
            "descricao": "Dúvida geral sobre o sistema operacional.",
        })
        self.assertFalse(form_sla_invalido.is_valid())
        self.assertTrue(any("não pode ser anterior ou igual à data de abertura" in err for err in form_sla_invalido.non_field_errors()))

        # 5. Validação no ResolverChamadoForm: fechar chamado sem solução técnica deve falhar
        chamado = Chamado.objects.create(
            titulo="Queda de VPN Corporativa",
            descricao="Usuários remotos sem comunicação com a matriz.",
            solicitante_nome="Roberto",
            solicitante_email="roberto@empresa.com",
            categoria=self.categoria,
            prioridade=self.prioridade,
            status="aberto",
            organizacao=self.org_a,
        )
        form_resolver_invalido = ResolverChamadoForm(instance=chamado, data={
            "status": "resolvido",
            "solucao": "Ok",
        })
        self.assertFalse(form_resolver_invalido.is_valid())
        self.assertIn("solucao", form_resolver_invalido.errors)


class MultiTenantIsolamentoTestes(TestCase):
    """
    Roteiro Oficial de Testes de Isolamento Multi-tenant (Aula 14, slide 18):
    1. Usuário A abre a lista de chamados: vê só os da organização A.
    2. Usuário A abre /chamado/ID-da-B/: recebe 404 (prevenção de IDOR).
    3. Usuário A cria um chamado: gravado com a organização A.
    4. Formulário do usuário A: selects mostram só opções da organização A.
    5. Unicidade de protocolo é por organização.
    """

    def setUp(self):
        self.client_a = Client()
        self.client_b = Client()

        self.org_a = Organizacao.objects.create(nome="Hospital São Lucas")
        self.org_b = Organizacao.objects.create(nome="Universidade Central")

        self.user_a = User.objects.create_user(username="operador_a", password="123")
        self.perfil_a = Perfil.objects.create(usuario=self.user_a, organizacao=self.org_a, papel="operador")
        self.client_a.force_login(self.user_a)

        self.user_b = User.objects.create_user(username="operador_b", password="123")
        self.perfil_b = Perfil.objects.create(usuario=self.user_b, organizacao=self.org_b, papel="operador")
        self.client_b.force_login(self.user_b)

        self.prio = Prioridade.objects.create(nivel="media", nome="Média", peso=2)
        SLA.objects.create(prioridade=self.prio, horas_resolucao=24)

        self.equipe_a = Equipe.objects.create(nome="TI Hospital", email_contato="ti@hospital.com", organizacao=self.org_a)
        self.cat_a = Categoria.objects.create(nome="Prontuário Eletrônico", equipe=self.equipe_a, organizacao=self.org_a)

        self.equipe_b = Equipe.objects.create(nome="TI Campus", email_contato="ti@universidade.edu", organizacao=self.org_b)
        self.cat_b = Categoria.objects.create(nome="Portal do Aluno", equipe=self.equipe_b, organizacao=self.org_b)

        self.chamado_a = Chamado.objects.create(
            titulo="Falha no Prontuário Médico",
            descricao="Sistema de prescrição não abre.",
            solicitante_nome="Dra. Paula",
            solicitante_email="paula@hospital.com",
            categoria=self.cat_a,
            prioridade=self.prio,
            organizacao=self.org_a,
        )
        self.chamado_b = Chamado.objects.create(
            titulo="Matrícula Não Carrega",
            descricao="Erro 500 ao confirmar matrícula semestral.",
            solicitante_nome="Pedro Aluno",
            solicitante_email="pedro@universidade.edu",
            categoria=self.cat_b,
            prioridade=self.prio,
            organizacao=self.org_b,
        )

    def test_usuario_a_abre_lista_e_ve_so_chamados_da_org_a(self):
        resp_a = self.client_a.get(reverse("index"))
        self.assertContains(resp_a, "Falha no Prontuário Médico")
        self.assertNotContains(resp_a, "Matrícula Não Carrega")

        resp_b = self.client_b.get(reverse("index"))
        self.assertContains(resp_b, "Matrícula Não Carrega")
        self.assertNotContains(resp_b, "Falha no Prontuário Médico")

    def test_usuario_a_abre_id_da_org_b_retorna_404(self):
        """Prevenção de IDOR: acessar o ID de outra organização retorna 404."""
        resp = self.client_a.get(reverse("detalhes_chamado", args=[self.chamado_b.id]))
        self.assertEqual(resp.status_code, 404)

    def test_usuario_a_cria_chamado_gravado_com_org_a(self):
        resp = self.client_a.post(reverse("novo_chamado"), {
            "titulo": "Impressora do Bloco Cirúrgico Travada",
            "categoria": self.cat_a.id,
            "prioridade": self.prio.id,
            "solicitante_nome": "Enfermeira Chefe",
            "solicitante_email": "enf@hospital.com",
            "descricao": "Impressora térmica de pulseiras não responde.",
        })
        self.assertEqual(resp.status_code, 302)
        novo = Chamado.objects.get(titulo="Impressora do Bloco Cirúrgico Travada")
        self.assertEqual(novo.organizacao, self.org_a)

    def test_formulario_selects_mostram_apenas_categorias_da_org_a(self):
        resp = self.client_a.get(reverse("novo_chamado"))
        self.assertContains(resp, "Prontuário Eletrônico")
        self.assertNotContains(resp, "Portal do Aluno")

    def test_tentativa_de_usar_categoria_de_outra_org_no_form_e_rejeitada(self):
        form = ChamadoForm(org=self.org_a, data={
            "titulo": "Tentativa Invasiva de Submissão",
            "categoria": self.cat_b.id, # Categoria da Org B
            "prioridade": self.prio.id,
            "solicitante_nome": "Hacker",
            "solicitante_email": "hacker@teste.com",
            "descricao": "Tentando injetar categoria de outra organização.",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("categoria", form.errors)

    def test_unicidade_de_protocolo_por_organizacao(self):
        """Duas organizações diferentes podem ter o mesmo número de protocolo."""
        c_a = Chamado.objects.create(
            protocolo="HD-2026-9999",
            titulo="Chamado Exemplo A",
            descricao="Descrição de teste para organização A.",
            solicitante_nome="Pessoa A",
            solicitante_email="a@hospital.com",
            categoria=self.cat_a,
            prioridade=self.prio,
            organizacao=self.org_a,
        )
        c_b = Chamado.objects.create(
            protocolo="HD-2026-9999", # Mesmo protocolo, mas na Org B
            titulo="Chamado Exemplo B",
            descricao="Descrição de teste para organização B.",
            solicitante_nome="Pessoa B",
            solicitante_email="b@universidade.edu",
            categoria=self.cat_b,
            prioridade=self.prio,
            organizacao=self.org_b,
        )
        self.assertEqual(c_a.protocolo, c_b.protocolo)
        self.assertNotEqual(c_a.organizacao, c_b.organizacao)


class ApiRestDRFTestes(TestCase):
    """
    Testes da API REST DRF (Aula 13 & 14):
    1. Endpoint requer autenticação.
    2. GET /api/chamados/ retorna apenas registros da organização do usuário.
    3. POST /api/chamados/ injeta a organização automaticamente.
    4. GET /api/chamados/<pk>/ de outra organização retorna 404.
    """

    def setUp(self):
        self.client = Client()
        self.org_a = Organizacao.objects.create(nome="Tech Corp")
        self.org_b = Organizacao.objects.create(nome="Finance Corp")

        self.user_a = User.objects.create_user(username="api_user_a", password="123")
        self.perfil_a = Perfil.objects.create(usuario=self.user_a, organizacao=self.org_a)

        self.user_b = User.objects.create_user(username="api_user_b", password="123")
        self.perfil_b = Perfil.objects.create(usuario=self.user_b, organizacao=self.org_b)

        self.prio = Prioridade.objects.create(nivel="alta", nome="Alta", peso=2)
        SLA.objects.create(prioridade=self.prio, horas_resolucao=8)

        self.eq_a = Equipe.objects.create(nome="DevOps", email_contato="devops@tech.com", organizacao=self.org_a)
        self.cat_a = Categoria.objects.create(nome="CI/CD Pipeline", equipe=self.eq_a, organizacao=self.org_a)

        self.eq_b = Equipe.objects.create(nome="Contábil", email_contato="contabil@fin.com", organizacao=self.org_b)
        self.cat_b = Categoria.objects.create(nome="Folha de Pagamento", equipe=self.eq_b, organizacao=self.org_b)

        self.ch_a = Chamado.objects.create(
            titulo="Pipeline Travado no Git",
            descricao="Build falhando por falta de espaço no runner.",
            solicitante_nome="Dev João",
            solicitante_email="joao@tech.com",
            categoria=self.cat_a,
            prioridade=self.prio,
            organizacao=self.org_a,
        )
        self.ch_b = Chamado.objects.create(
            titulo="Erro no SPED Fiscal",
            descricao="Arquivo com erro de leiaute na transmissão.",
            solicitante_nome="Contador José",
            solicitante_email="jose@fin.com",
            categoria=self.cat_b,
            prioridade=self.prio,
            organizacao=self.org_b,
        )

    def test_api_requer_autenticacao(self):
        resp = self.client.get(reverse("api_chamados_list_create"))
        self.assertEqual(resp.status_code, 403)

    def test_api_retorna_apenas_chamados_da_propria_org(self):
        self.client.force_login(self.user_a)
        resp = self.client.get(reverse("api_chamados_list_create"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        titulos = [item["titulo"] for item in data["results"] if "results" in data] or [item["titulo"] for item in data]
        self.assertIn("Pipeline Travado no Git", titulos)
        self.assertNotIn("Erro no SPED Fiscal", titulos)

    def test_api_post_inicia_chamado_com_org_do_usuario(self):
        self.client.force_login(self.user_a)
        resp = self.client.post(
            reverse("api_chamados_list_create"),
            data={
                "titulo": "Novo Pod Kubernetes em CrashLoop",
                "descricao": "Pod de autenticação falhando após deploy.",
                "solicitante_nome": "SRE Maria",
                "solicitante_email": "maria@tech.com",
                "categoria": self.cat_a.id,
                "prioridade": self.prio.id,
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["titulo"], "Novo Pod Kubernetes em CrashLoop")
        chamado = Chamado.objects.get(id=data["id"])
        self.assertEqual(chamado.organizacao, self.org_a)

    def test_api_detalhes_de_outra_org_retorna_404(self):
        self.client.force_login(self.user_a)
        resp = self.client.get(reverse("api_chamados_detail", args=[self.ch_b.id]))
        self.assertEqual(resp.status_code, 404)


class DashboardERelatoriosTestes(TestCase):
    """
    Testes de Dashboard, Relatórios e Desempenho (Aula 17):
    1. aggregate e annotate calculam KPIs e ranking corretamente.
    2. PeriodoForm valida datas e evita erros 500.
    3. Exportação CSV filtra por organização e período.
    4. Desempenho: assertNumQueries prova eliminação de N+1 consultas.
    """

    def setUp(self):
        self.client = Client()
        self.org = Organizacao.objects.create(nome="Logística Global")
        self.user = User.objects.create_user(username="gerente_op", password="123")
        self.perfil = Perfil.objects.create(usuario=self.user, organizacao=self.org, papel="admin")
        self.client.force_login(self.user)

        self.prio = Prioridade.objects.create(nivel="alta", nome="Alta", peso=2)
        SLA.objects.create(prioridade=self.prio, horas_resolucao=12)

        self.equipe = Equipe.objects.create(nome="Rastreamento", email_contato="rastreio@log.com", organizacao=self.org)
        self.cat1 = Categoria.objects.create(nome="Carga Extraviada", equipe=self.equipe, organizacao=self.org)
        self.cat2 = Categoria.objects.create(nome="Atraso de Entrega", equipe=self.equipe, organizacao=self.org)

        # Criar chamados
        Chamado.objects.create(
            titulo="Caminhão parado na rodovia",
            descricao="Pane mecânica no cavalo mecânico.",
            solicitante_nome="Motorista João",
            solicitante_email="joao@log.com",
            categoria=self.cat1,
            prioridade=self.prio,
            status="aberto",
            organizacao=self.org,
        )
        Chamado.objects.create(
            titulo="Pacote sem atualização há 48h",
            descricao="Cliente cobrando posição de entrega urgente.",
            solicitante_nome="SAC Central",
            solicitante_email="sac@log.com",
            categoria=self.cat2,
            prioridade=self.prio,
            status="resolvido",
            solucao="Localizado no centro de distribuição de Campinas e liberado.",
            data_resolucao=timezone.now(),
            organizacao=self.org,
        )

    def test_dashboard_carrega_com_sucesso(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dashboard de Operações & SLA")
        self.assertContains(resp, "Logística Global")
        self.assertContains(resp, "Carga Extraviada")
        self.assertContains(resp, "Atraso de Entrega")

    def test_filtro_periodo_invalido_nao_gera_500(self):
        """Aula 17, slide 11: strings inválidas na URL não podem causar erro 500."""
        resp = self.client.get(reverse("dashboard") + "?inicio=texto_invalido&fim=2026-99-99")
        self.assertEqual(resp.status_code, 200)

    def test_exportar_csv_gera_arquivo_correto(self):
        resp = self.client.get(reverse("exportar_csv"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn('filename="relatorio_chamados.csv"', resp["Content-Disposition"])
        content = resp.content.decode("utf-8")
        self.assertIn("Caminhão parado na rodovia", content)
        self.assertIn("Pacote sem atualização há 48h", content)

    def test_assert_num_queries_sem_n_mais_um(self):
        """
        Aula 17, slides 19-31: Travar desempenho com assertNumQueries.
        Ao iterar sobre chamados com select_related('categoria', 'prioridade'),
        deve ser executada exatamente 1 consulta SQL (com INNER JOIN), evitando N+1 consultas.
        """
        # Criar mais 3 chamados para tornar N perceptível
        for i in range(3):
            Chamado.objects.create(
                titulo=f"Incidente de Rota {i}",
                descricao="Problema no tráfego da rodovia estadual.",
                solicitante_nome=f"Motorista {i}",
                solicitante_email=f"motorista{i}@log.com",
                categoria=self.cat1,
                prioridade=self.prio,
                organizacao=self.org,
            )

        # Com select_related, exatamente 1 consulta carrega chamados, categoria e prioridade
        with self.assertNumQueries(1):
            qs = Chamado.objects.filter(organizacao=self.org).select_related("categoria", "prioridade")
            for c in qs:
                _ = c.categoria.nome
                _ = c.prioridade.nome
