# Relatório de Dívida Técnica e Melhorias P1 → P2

**Disciplina:** Laboratório de Programação Full Stack  
**Professor:** Márcio Garrido  
**Aluno:** Marcos Vinícius Silva Estrela  
**Matrícula:** 202413893  
**Projeto:** Help Desk & Gestão de SLA de Chamados (Opção 4)  

---

## 📌 Contexto
Conforme apresentado na **Aula 13 (DRF e Planejamento P2)** e **Aula 14 (Multi-organização: Isolamento de Dados)**, a evolução do sistema para um modelo SaaS / multi-tenant e a exposição de APIs REST herdam diretamente a solidez do modelo de dados da P1. Qualquer fragilidade, acoplamento indevido ou ausência de validação na P1 se propagaria para as novas camadas (API, Dashboard e isolamento entre clientes).

Este documento registra as principais dívidas técnicas identificadas no encerramento da P1, as justificativas de engenharia e como foram resolvidas na arquitetura da P2.

---

## 🛠️ Itens de Melhoria e Refatoração

### 1. Ausência de Isolamento Multi-Inquilino (Multi-Tenancy)
* **Situação na P1:** O sistema tratava todos os dados como pertencentes a um único ambiente global (monolítico mono-organização). Chamados, categorias e equipes não possuíam vínculo organizacional, impedindo a coexistência de múltiplas empresas ou departamentos independentes no mesmo banco de dados.
* **Impacto:** Risco crítico de vazamento de dados corporativos (data leakage), tornando o sistema inviável como solução de mercado.
* **Solução na P2:**
  - Criação do app `core` contendo os models `Organizacao`, `Perfil` (vinculando `User` a uma `Organizacao` com papel de acesso) e a classe base abstrata `DaOrganizacao`.
  - Herança de `DaOrganizacao` nas entidades de negócio (`Chamado`, `Categoria`, `Equipe`).
  - Execução de estratégia de migração em 3 etapas com `RunPython` (`0002`, `0003_dados_org` e `0004`), preservando os registros existentes na P1 sem perda de dados.
  - Injeção obrigatória do filtro `organizacao=org_atual(request)` em todas as consultas ORM, formulários, rotas de detalhe e endpoints da API.

---

### 2. Fragilidade de Unicidade Global de Protocolos
* **Situação na P1:** O campo `protocolo` no model `Chamado` utilizava a restrição `unique=True` em nível de tabela inteira.
* **Impacto:** Conforme discutido na Aula 14 (slide 16), uma unicidade global impede que duas organizações clientes independentes compartilhem a mesma convenção ou numeração de protocolo no mesmo ano (ex: `HD-2026-1001`), forçando colisões entre clientes.
* **Solução na P2:**
  - Remoção de `unique=True` global do campo `protocolo`.
  - Aplicação de `UniqueConstraint(fields=['organizacao', 'protocolo'], name='chamado_protocolo_unico_por_org')`.
  - Refatoração do método `save()` do `Chamado` para calcular a sequência de protocolos isoladamente por inquilino.

---

### 3. Vulnerabilidade Potencial de Acesso Direto a Objetos (IDOR em Rotas)
* **Situação na P1:** A view `detalhes_chamado` realizava a busca através de `get_object_or_404(Chamado, id=chamado_id)` sem checar propriedade ou contexto do usuário.
* **Impacto:** Um usuário autenticado poderia manipular o ID na barra de endereço (ex: trocar `/chamado/1/` por `/chamado/2/`) e visualizar ou alterar incidentes de outra organização.
* **Solução na P2:**
  - Ajuste para `get_object_or_404(Chamado, id=chamado_id, organizacao=org_atual(request))`.
  - Caso o ID pertença a outra organização, a aplicação responde imediatamente com código `HTTP 404 (Not Found)`, não revelando sequer a existência do registro para terceiros.

---

### 4. Vulnerabilidade de Vazamento em Elementos Select de Formulários
* **Situação na P1:** O `ChamadoForm` utilizava o queryset padrão do `ModelForm`, listando indistintamente todas as categorias ativas do banco de dados no elemento `<select>`.
* **Impacto:** Ao tentar abrir um chamado, um operador da Organização A visualizava as categorias internas e equipes confidenciais da Organização B.
* **Solução na P2:**
  - Sobrescrita do construtor `__init__(self, *args, org=None, **kwargs)` no `ChamadoForm`.
  - Filtro explícito `self.fields['categoria'].queryset = Categoria.objects.filter(organizacao=org, ativa=True)`.
  - Validação cruzada no método `clean()` para rejeitar qualquer tentativa de injeção de ID de categoria externa.

---

### 5. Consultas N+1 em Listagens e Relatórios (Desempenho de Banco)
* **Situação na P1:** A iteração sobre chamados na view ou template acessava as relações de `categoria`, `prioridade` e `equipe` de forma lazy, gerando dezenas de consultas SQL repetitivas e duplicadas.
* **Impacto:** Degradação severa de performance e aumento desnecessário de latência no banco de dados com o crescimento do volume de chamados.
* **Solução na P2 (Aula 17):**
  - Implementação sistemática de `select_related('categoria', 'prioridade', 'categoria__equipe')` na view principal, na exportação CSV e na API REST.
  - Criação de testes de desempenho travando as consultas com `self.assertNumQueries(1)` para garantir a ausência de consultas adicionais durante a renderização e relatórios.

---

### 6. Ausência de Interface de Dados Programática (API REST)
* **Situação na P1:** A aplicação funcionava estritamente como renderizadora de templates HTML server-side via Django Templates.
* **Impacto:** Impossibilidade de integração com sistemas terceiros, bots de monitoramento de infraestrutura (Zabbix, Grafana) ou aplicativos mobile.
* **Solução na P2 (Aula 13):**
  - Configuração do Django REST Framework (`rest_framework`).
  - Criação de serializers estruturados (`ChamadoSerializer`, `CategoriaSerializer`, `PrioridadeSerializer`).
  - Disponibilização de rotas com generics (`ListCreateAPIView`, `RetrieveUpdateDestroyAPIView`), autenticação e permissões restritas à organização do requisitante.
