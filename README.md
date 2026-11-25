# 🎫 Help Desk & Gestão de SLA de Chamados — P1 & P2 (Mini-SaaS)

**Disciplina:** Laboratório de Programação Full Stack  
**Professor:** Márcio Garrido  
**Aluno:** Marcos Vinícius Silva Estrela  
**Matrícula:** 202413893  
**Avaliação:** P1 (MVP Funcional) + P2 (Multi-organização, DRF REST API, Dashboard e Relatórios)  
**Tema Escolhido:** Opção 4 — Help Desk / Chamados com Gestão de SLA  

---

## 📌 1. Visão Geral da Arquitetura

O projeto evoluiu de um MVP monofolha (P1) para uma plataforma **Mini-SaaS Multi-tenant** (P2), atendendo integralmente ao conteúdo pedagógico das **Aulas 13 (DRF)**, **14 (Multi-organização: Isolamento de Dados)** e **17 (Dashboard e Relatórios)**.

### As Entidades do Sistema:
1. **`core.Organizacao`**: Inquilino/empresa dona dos dados.
2. **`core.Perfil`**: Vínculo 1:1 com `auth.User`, definindo a organização e o papel (`admin` ou `operador`).
3. **`helpdesk.Equipe`**: Grupos técnicos de suporte (vinculada à organização via `DaOrganizacao`).
4. **`helpdesk.Categoria`**: Tipos de incidentes vinculados à equipe e à organização.
5. **`helpdesk.Prioridade`**: Níveis de urgência (`Crítica`, `Alta`, `Média`, `Baixa`).
6. **`helpdesk.SLA`**: Tempo máximo em horas contratado para resolução conforme a prioridade.
7. **`helpdesk.Chamado`**: Registro de ticket com protocolo, prazos automáticos de SLA, parecer técnico e isolamento por inquilino.

---

## 🏢 2. Multi-organização: Isolamento de Dados (Aula 14)

### Estratégia Escolhida: Coluna Discriminadora
Conforme preconizado na Aula 14 (slide 6), foi adotada a estratégia de **Coluna Discriminadora** através de chave estrangeira (`ForeignKey('core.Organizacao', on_delete=models.PROTECT)`), viabilizada pela classe abstrata `DaOrganizacao`.

### Migração sem Perda de Dados em 3 Etapas (Slides 9 e 10):
1. **`0002_add_org_fields`**: Adição das FKs de organização em `Equipe`, `Categoria` e `Chamado` com `null=True`.
2. **`0003_dados_org`**: Migração de dados via `migrations.RunPython`, preenchendo automaticamente todos os registros existentes da P1 com uma `Organização Padrão`.
3. **`0004_alter_org_not_null_and_constraints`**: Conversão das FKs para `null=False`, remoção de unicidade global de protocolos e aplicação de `UniqueConstraint` e índices por organização.

### Blindagem de Segurança Aplicada:
* **`org_atual(request)`**: Ponto único centralizador em `core/utils.py` que obtém a organização do usuário logado.
* **Toda Consulta Filtra:** Todas as views e querysets partem de `filter(organizacao=org)`.
* **Criação de Registros com `commit=False`:** A organização é atribuída programaticamente a partir da sessão do usuário logado; o campo `organizacao` nunca é exposto em formulários HTML.
* **Proteção contra IDOR (Acesso Indevido por ID):** Rotas de detalhes utilizam `get_object_or_404(Chamado, id=id, organizacao=org)`. IDs de outras organizações retornam **HTTP 404**, sem vazar a existência do recurso.
* **Selects Blindados:** O `<select>` de categorias filtra estritamente `Categoria.objects.filter(organizacao=org, ativa=True)`.
* **Unicidade Escopada por Tenant:** Unicidade de protocolo alterada de global para `UniqueConstraint(fields=['organizacao', 'protocolo'])`. Clientes distintos podem ter protocolos com mesmo identificador sem conflito.

---

## ⚡ 3. API REST com Django REST Framework (Aula 13)

Endpoints REST estruturados com autenticação por sessão/básico e permissão `IsAuthenticated`:

| Método | Endpoint | Descrição | Isolamento Multi-tenant |
|---|---|---|---|
| `GET` | `/api/chamados/` | Lista chamados com paginação | Apenas chamados da organização do usuário |
| `POST` | `/api/chamados/` | Abre novo chamado | Injeta organização atual no `perform_create` |
| `GET` | `/api/chamados/<id>/` | Detalha chamado específico | Retorna 404 se pertencer a outro inquilino |
| `PUT/PATCH`| `/api/chamados/<id>/` | Atualiza chamado | Restrito aos chamados da organização |
| `GET` | `/api/categorias/` | Lista categorias | Apenas categorias da organização |
| `POST` | `/api/categorias/` | Cadastra nova categoria | Vinculada à organização |
| `GET` | `/api/prioridades/`| Lista prioridades e SLAs | Tabela de referência |
| `GET` | `/api/dashboard/` | Métricas agregadas do dashboard | Responde JSON estruturado (Aula 17, slide 35) |

---

## 📊 4. Dashboard e Relatórios (Aula 17)

O painel `/dashboard/` responde a 4 perguntas analíticas essenciais do gestor:
1. **Totalizadores (KPIs com `aggregate`):**
   * Total de Chamados no período
   * Chamados Abertos / Em Atendimento
   * Chamados Resolvidos / Fechados
   * Chamados Fora do Prazo (SLA Violado/Estourado)
2. **Ranking (Top 5 com `values() + annotate(Count) + order_by`):**
   * Categorias de incidente com maior demanda.
3. **Série Temporal (`TruncMonth`):**
   * Agrupamento mensal da abertura de chamados com ordenação cronológica.
4. **Distribuição (`values() + annotate(Count)`):**
   * Proporção de incidentes por prioridade.

### Filtro por Período Validado (`PeriodoForm`):
Protege o sistema contra strings malformadas na URL (`?inicio=...&fim=...`), evitando erros 500 decorrentes de parâmetros inválidos.

### Gráficos com Chart.js (`json_script`):
Os dados agregados pelo ORM são serializados no template de forma segura via `{{ dados_mes|json_script:"dados-mes" }}` e renderizados dinamicamente pelo Chart.js.

### Exportação em CSV (`/chamados/exportar/`):
Exporta o relatório consolidado de chamados em formato tabular com cabeçalhos formatados e encoding UTF-8 com BOM (compatível com Microsoft Excel), respeitando a organização e os filtros de período aplicados.

### Prevenção de Consultas N+1:
Implementação de `select_related('categoria', 'prioridade', 'categoria__equipe')` em todas as rotas de listagem, detalhes e exportação. Validado via teste automatizado com `assertNumQueries(1)`.

---

## 🧪 5. Testes Automatizados e Prova de Isolamento

A suíte de testes automatizados cobre 100% dos fluxos da P1 e as novas exigências da P2:

```bash
python manage.py test
```

### Resultados da Execução:
* **`HelpDeskP1Testes`**:
  * Criação das entidades base (Equipe, Categoria, Prioridade, SLA, Chamado).
  * Acesso HTTP 200 nas rotas principais.
  * Cálculo automático de prazo de SLA e transição de status para resolvido.
  * Feature 1: Busca textual e filtros combinados com `Q()`.
  * Feature 2: Validações customizadas de SLA, chamados críticos e encerramento técnico.
* **`MultiTenantIsolamentoTestes`** (Roteiro da Aula 14, slide 18):
  * `test_usuario_a_abre_lista_e_ve_so_chamados_da_org_a` (✅ Aprovado)
  * `test_usuario_a_abre_id_da_org_b_retorna_404` (✅ Aprovado)
  * `test_usuario_a_cria_chamado_gravado_com_org_a` (✅ Aprovado)
  * `test_formulario_selects_mostram_apenas_categorias_da_org_a` (✅ Aprovado)
  * `test_tentativa_de_usar_categoria_de_outra_org_no_form_e_rejeitada` (✅ Aprovado)
  * `test_unicidade_de_protocolo_por_organizacao` (✅ Aprovado)
* **`ApiRestDRFTestes`** (Aula 13):
  * `test_api_requer_autenticacao` (✅ Aprovado)
  * `test_api_retorna_apenas_chamados_da_propria_org` (✅ Aprovado)
  * `test_api_post_inicia_chamado_com_org_do_usuario` (✅ Aprovado)
  * `test_api_detalhes_de_outra_org_retorna_404` (✅ Aprovado)
* **`DashboardERelatoriosTestes`** (Aula 17):
  * `test_dashboard_carrega_com_sucesso` (✅ Aprovado)
  * `test_filtro_periodo_invalido_nao_gera_500` (✅ Aprovado)
  * `test_exportar_csv_gera_arquivo_correto` (✅ Aprovado)
  * `test_assert_num_queries_sem_n_mais_um` (✅ Aprovado - trava performance com `assertNumQueries(1)`)

---

## 🚀 6. Como Executar Localmente

### Pré-requisitos:
* Python 3.10+
* Virtualenv configurado

```bash
# 1. Clonar e entrar no repositório
git clone https://github.com/Marcos-Estrela16/marcio_p1_helpdesk.git
cd marcio_p1_helpdesk

# 2. Criar e ativar ambiente virtual
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Executar as migrações (incluindo migração de dados de multi-tenancy)
python manage.py migrate

# 5. Executar os testes automatizados
python manage.py test

# 6. Iniciar o servidor
python manage.py runserver
```

Acesse:
* **Aplicação Web:** `http://127.0.0.1:8000/`
* **Dashboard & Relatórios:** `http://127.0.0.1:8000/dashboard/`
* **API REST DRF:** `http://127.0.0.1:8000/api/chamados/`
* **Django Admin:** `http://127.0.0.1:8000/admin/`

---

## 📄 7. Documentos Complementares
* **[`MELHORIAS_P1.md`](MELHORIAS_P1.md)**: Relatório de dívida técnica, justificativas de arquitetura e refatorações realizadas na transição P1 → P2 (Aula 13, slide 5).
