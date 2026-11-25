from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import Organizacao, Perfil
from helpdesk.models import Prioridade, SLA, Equipe, Categoria, Chamado

class Command(BaseCommand):
    help = "Popula o banco de dados com dados iniciais para demonstração da P2 (Multi-tenancy, DRF e Dashboard)"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando carga de dados para demonstração da P2...")

        # 1. Prioridades e SLAs
        prios_data = [
            ("critica", "Crítica", 1, "danger", 2, "Atendimento imediato 24x7"),
            ("alta", "Alta", 2, "warning", 8, "Prazo útil no mesmo dia"),
            ("media", "Média", 3, "primary", 24, "Prazo de até 24 horas úteis"),
            ("baixa", "Baixa", 4, "success", 72, "Prazo de até 3 dias úteis"),
        ]
        prios = {}
        for nivel, nome, peso, cor, horas, desc in prios_data:
            prio, _ = Prioridade.objects.get_or_create(
                nivel=nivel,
                defaults={"nome": nome, "peso": peso, "cor_badge": cor}
            )
            SLA.objects.get_or_create(
                prioridade=prio,
                defaults={"horas_resolucao": horas, "descricao": desc}
            )
            prios[nivel] = prio
        self.stdout.write(self.style.SUCCESS("✓ Prioridades e Acordos de SLA criados."))

        # 2. Organizações (Multi-tenancy)
        org_a, _ = Organizacao.objects.get_or_create(nome="Hospital São Lucas")
        org_b, _ = Organizacao.objects.get_or_create(nome="Universidade Central")
        self.stdout.write(self.style.SUCCESS("✓ Organizações criadas (Hospital São Lucas e Universidade Central)."))

        # 3. Usuários e Perfis
        # Admin Global
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser("admin", "admin@suporte.com", "admin123")
            Perfil.objects.create(usuario=admin, organizacao=org_a, papel="admin")
            self.stdout.write(self.style.SUCCESS("✓ Superusuário 'admin' criado (senha: admin123)."))
        else:
            admin = User.objects.get(username="admin")
            Perfil.objects.get_or_create(usuario=admin, defaults={"organizacao": org_a, "papel": "admin"})

        # Operador Org A
        if not User.objects.filter(username="operador_hospital").exists():
            u_a = User.objects.create_user("operador_hospital", "op_hospital@saolucas.com", "senha123")
            Perfil.objects.create(usuario=u_a, organizacao=org_a, papel="operador")
            self.stdout.write(self.style.SUCCESS("✓ Operador 'operador_hospital' criado (senha: senha123)."))

        # Operador Org B
        if not User.objects.filter(username="operador_univ").exists():
            u_b = User.objects.create_user("operador_univ", "op_univ@central.edu", "senha123")
            Perfil.objects.create(usuario=u_b, organizacao=org_b, papel="operador")
            self.stdout.write(self.style.SUCCESS("✓ Operador 'operador_univ' criado (senha: senha123)."))

        # 4. Equipes e Categorias por Organização
        # Org A
        eq_med, _ = Equipe.objects.get_or_create(
            nome="TI Clínica",
            organizacao=org_a,
            defaults={"email_contato": "ti.clinica@saolucas.com"}
        )
        cat_pront, _ = Categoria.objects.get_or_create(
            nome="Prontuário Eletrônico",
            equipe=eq_med,
            organizacao=org_a,
            defaults={"descricao": "Sistemas de prescrição médica e histórico de leitos"}
        )
        cat_pacs, _ = Categoria.objects.get_or_create(
            nome="Sistemas de Imagem / PACS",
            equipe=eq_med,
            organizacao=org_a,
            defaults={"descricao": "Laudos radiológicos e tomografia"}
        )

        eq_infra_a, _ = Equipe.objects.get_or_create(
            nome="Infraestrutura Hospitalar",
            organizacao=org_a,
            defaults={"email_contato": "infra@saolucas.com"}
        )
        cat_wifi, _ = Categoria.objects.get_or_create(
            nome="Rede Wi-Fi dos Leitos",
            equipe=eq_infra_a,
            organizacao=org_a,
            defaults={"descricao": "Conectividade de telemetria e tablets médicos"}
        )

        # Org B
        eq_acad, _ = Equipe.objects.get_or_create(
            nome="Sistemas Acadêmicos",
            organizacao=org_b,
            defaults={"email_contato": "sistemas@central.edu"}
        )
        cat_portal, _ = Categoria.objects.get_or_create(
            nome="Portal do Aluno",
            equipe=eq_acad,
            organizacao=org_b,
            defaults={"descricao": "Matrículas, notas e financeiro estudantil"}
        )
        cat_moodle, _ = Categoria.objects.get_or_create(
            nome="Ambiente Virtual Moodle",
            equipe=eq_acad,
            organizacao=org_b,
            defaults={"descricao": "Salas de aula virtuais e entregas de trabalhos"}
        )
        self.stdout.write(self.style.SUCCESS("✓ Equipes e Categorias cadastradas e isoladas por organização."))

        # 5. Chamados de Exemplo para Hospital São Lucas
        agora = timezone.now()
        chamados_hospital = [
            (
                "Lentidão no Módulo de Prescrição Médica",
                "Médicos do plantão de emergência relatam tempo de resposta superior a 15 segundos ao liberar antibióticos.",
                "Dra. Mariana Costa",
                "mariana@saolucas.com",
                cat_pront,
                prios["critica"],
                "aberto",
                agora - timedelta(hours=3),
                None,
                "",
            ),
            (
                "Falha de Sincronismo no Servidor PACS de Ressonância",
                "Exames realizados na manhã de hoje não estão carregando na estação de laudo do Bloco B.",
                "Dr. Roberto Alencar",
                "roberto@saolucas.com",
                cat_pacs,
                prios["alta"],
                "em_atendimento",
                agora - timedelta(hours=5),
                None,
                "",
            ),
            (
                "Ponto de Acesso Wi-Fi do 4º Andar Offline",
                "Tablets da equipe de enfermagem desconectando durante checagem de medicação nos leitos 401 a 412.",
                "Enf. Juliana Mendes",
                "juliana@saolucas.com",
                cat_wifi,
                prios["media"],
                "resolvido",
                agora - timedelta(days=2),
                agora - timedelta(days=1, hours=20),
                "Substituído injetor PoE do switch de distribuição e reconectado o AP.",
            ),
            (
                "Impressora Térmica do Pronto Socorro Travada",
                "Fila de impressão acumulando etiquetas de triagem de Manchester.",
                "Atendente Carlos",
                "carlos@saolucas.com",
                cat_pront,
                prios["alta"],
                "resolvido",
                agora - timedelta(days=5),
                agora - timedelta(days=5, hours=2),
                "Desobstruído rolete de tração da impressora e calibrado o sensor de papel.",
            ),
        ]

        for tit, desc, sol_nome, sol_email, cat, prio, st, dt_ab, dt_res, soluc in chamados_hospital:
            if not Chamado.objects.filter(titulo=tit, organizacao=org_a).exists():
                c = Chamado(
                    titulo=tit,
                    descricao=desc,
                    solicitante_nome=sol_nome,
                    solicitante_email=sol_email,
                    categoria=cat,
                    prioridade=prio,
                    status=st,
                    organizacao=org_a,
                )
                c.save()
                # Ajusta datas retroativas para série temporal e KPIs
                Chamado.objects.filter(id=c.id).update(
                    data_abertura=dt_ab,
                    prazo_sla=dt_ab + timedelta(hours=prio.sla.horas_resolucao),
                    data_resolucao=dt_res,
                    solucao=soluc,
                )

        # 6. Chamados de Exemplo para Universidade Central
        chamados_univ = [
            (
                "Erro 502 ao Confirmar Matrícula Semestral",
                "Pico de acessos às 08h derrubou os pods do serviço de rematrícula online.",
                "Secretaria Acadêmica",
                "secretaria@central.edu",
                cat_portal,
                prios["critica"],
                "aberto",
                agora - timedelta(hours=1),
                None,
                "",
            ),
            (
                "Vídeos da Disciplina de Cálculo não Carregam no Moodle",
                "Alunos notificando erro de timeout ao carregar arquivos MP4 das aulas gravadas.",
                "Prof. Fernando Dias",
                "fernando@central.edu",
                cat_moodle,
                prios["media"],
                "em_atendimento",
                agora - timedelta(hours=10),
                None,
                "",
            ),
        ]

        for tit, desc, sol_nome, sol_email, cat, prio, st, dt_ab, dt_res, soluc in chamados_univ:
            if not Chamado.objects.filter(titulo=tit, organizacao=org_b).exists():
                c = Chamado(
                    titulo=tit,
                    descricao=desc,
                    solicitante_nome=sol_nome,
                    solicitante_email=sol_email,
                    categoria=cat,
                    prioridade=prio,
                    status=st,
                    organizacao=org_b,
                )
                c.save()
                Chamado.objects.filter(id=c.id).update(
                    data_abertura=dt_ab,
                    prazo_sla=dt_ab + timedelta(hours=prio.sla.horas_resolucao),
                    data_resolucao=dt_res,
                    solucao=soluc,
                )

        self.stdout.write(self.style.SUCCESS("✓ Chamados de demonstração cadastrados com sucesso."))
        self.stdout.write(self.style.SUCCESS("\n🎉 Base de dados populada com sucesso!"))
        self.stdout.write("Contas disponíveis para teste:")
        self.stdout.write("  - Admin: 'admin' / 'admin123' (Org: Hospital São Lucas)")
        self.stdout.write("  - Operador Hospital: 'operador_hospital' / 'senha123' (Org: Hospital São Lucas)")
        self.stdout.write("  - Operador Universidade: 'operador_univ' / 'senha123' (Org: Universidade Central)")
