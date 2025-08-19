# Blue Sea Dashboard — v1 (Protótipo)

Este projeto cria um painel (dashboard) simples para **rentabilização de cotas** do Blue Sea Hotel.
- Feito em **Python + Streamlit** (roda localmente e pode ser publicado em nuvem).
- Permite **upload** de planilhas (CSV/XLSX) exportadas do seu sistema.
- Calcula **Receitas, Descontos e Repasse Líquido**, com base nas regras v1.
- Possui **tema visual** alinhado ao Blue Sea (cores ajustáveis no arquivo `.streamlit/config.toml`).

## 1) Requisitos
- Windows 10+ (ou macOS/Linux) com **Python 3.10+**
- Instalar dependências: `pip install -r requirements.txt`

## 2) Como rodar
1. Abra o Prompt/Terminal nesta pasta.
2. (Opcional) Crie um ambiente virtual:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate   # Windows
   # ou
   source .venv/bin/activate  # macOS/Linux
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Rode o app:
   ```bash
   streamlit run app.py
   ```
5. Abra o link mostrado (geralmente http://localhost:8501).

## 3) Como usar
- Na tela, faça **upload** do arquivo `CSV` ou `XLSX` com as colunas do modelo em `sample_data/template_rentabilizacao.csv`.
- Ajuste, na barra lateral, as **alíquotas/percentuais padrão** (ex.: comissão de parceiros, IRRF, mediana de cartão, etc.).
- Veja os **KPI’s** (Receita Bruta, Descontos Totais, Repasse Líquido, Take Rate) e o detalhamento por **Categoria, Canal e Cotista**.
- Baixe a **planilha processada** com todos os cálculos por reserva.

## 4) Regras v1 (parametrizáveis no app)
- **Impostos do Hotel (Lucro Presumido)**: 16,99% sobre o **valor bruto** da diária.
- **Café da manhã (POOL)**: por **dia** e por **pessoa**:
  - Adulto: R$ 50,00
  - Criança 7–12: R$ 25,00
  - Criança 0–6: **1 free** por reserva; as demais: R$ 25,00
- **Comissionamento**:
  - **Site**: taxa fixa **R$ 15,40** (OMNIBEES) por **reserva**.
  - **Parceiros externos** (Booking/Decolar/Operadoras): usar **percentual por canal** (padrão configurável ou coluna `taxa_parceiro_percent` na planilha).
  - **Walk-in / Telefone/WhatsApp**: sem comissão.
- **Taxa de cartão** (e antecipação): usar `taxa_cartao_percent` por reserva; se ausente e a forma for **cartão**, usar **mediana** do dataset ou um **padrão** configurável.
- **Taxa Administrativa do Hotel**: **10%** sobre o **valor líquido antes do IRRF**.
- **IRRF do Cotista**: alíquota **parametrizável** (por padrão, 0%). Valor calculado sobre o **líquido após taxa administrativa**.

> Observação: as regras acima refletem o comunicado interno atual. Você pode ajustar no app sem mexer no código.

## 5) Modelo de dados (colunas)
Veja `sample_data/template_rentabilizacao.csv`. Colunas esperadas:
- Identificação: `proprietario_id`, `proprietario_nome`, `categoria`, `unidade`, `cota`
- Reserva/Venda: `metodo_utilizacao` (POOL | USO PROPRIO | USO CONVIDADO), `canal_venda` (Walk-in, Telefone, Site, Booking, Decolar, Operadora...), `forma_pagamento` (cartao | pix | transferencia | dinheiro)
- Datas: `data_checkin`, `data_checkout`, `dias`
- Valores/Quantidades: `valor_bruto`, `qtd_adultos`, `qtd_criancas_7_12`, `qtd_criancas_0_6`
- Taxas (opcional por linha): `taxa_parceiro_percent`, `taxa_cartao_percent`, `desconto_campanha`, `estorno_devolucao`

## 6) Próximos passos (v2)
- Geração de **PDF por cotista**, com layout de marca (BrandBook) e capa personalizada.
- Integração de **fila de preferência por categoria** e destaque da próxima unidade.
- Conector direto com o sistema de reservas (quando viável).
- Painel com **metas por diária/categoria** e sazonalidade.
