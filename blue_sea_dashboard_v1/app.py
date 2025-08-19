
import io
import math
import base64
from datetime import datetime
from typing import Dict, Any, Tuple

import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------
# Page basics
# ---------------------------
st.set_page_config(
    page_title="Blue Sea - Dashboard de Rentabilização",
    page_icon="🌊",
    layout="wide",
)

st.markdown(
    '''
    <style>
    .metric-small .stMetric { padding: 0.25rem 0.5rem; }
    .brand-header {
        font-weight: 700;
        font-size: 1.4rem;
        margin: 0.25rem 0 1rem 0;
        letter-spacing: 0.4px;
    }
    .fine-print { color: #64748b; font-size: 0.9rem; }
    </style>
    ''',
    unsafe_allow_html=True
)

st.markdown('<div class="brand-header">Blue Sea Hotel — Dashboard de Rentabilização</div>', unsafe_allow_html=True)
st.caption("Protótipo v1 — upload de planilhas, cálculo de descontos e repasse líquido com transparência.")

# ---------------------------
# Sidebar — parâmetros
# ---------------------------
st.sidebar.header("⚙️ Parâmetros de Cálculo (v1)")

# Impostos (Lucro Presumido) sobre o valor bruto
aliquota_impostos = st.sidebar.number_input("Impostos (Lucro Presumido) — % sobre o bruto", min_value=0.0, max_value=100.0, value=16.99, step=0.01)

# Café da manhã (POOL) - por pessoa/dia
st.sidebar.subheader("Café da Manhã — valores por pessoa/dia (POOL)")
preco_cafe_adulto = st.sidebar.number_input("Adulto (R$)", min_value=0.0, value=50.0, step=1.0)
preco_cafe_crianca_7_12 = st.sidebar.number_input("Criança 7–12 (R$)", min_value=0.0, value=25.0, step=1.0)
preco_cafe_crianca_0_6 = st.sidebar.number_input("Criança 0–6 (R$)", min_value=0.0, value=25.0, step=1.0)
free_0_6 = st.sidebar.number_input("Qtde de crianças 0–6 com gratuidade por reserva", min_value=0, value=1, step=1)

# Parceiros/Comissões
st.sidebar.subheader("Comissionamento — padrão por canal (%)")
pct_booking = st.sidebar.number_input("Booking (%)", min_value=0.0, max_value=100.0, value=18.0, step=0.1)
pct_decolar = st.sidebar.number_input("Decolar (%)", min_value=0.0, max_value=100.0, value=20.0, step=0.1)
pct_operadora = st.sidebar.number_input("Operadora (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.1)
valor_omnibees = st.sidebar.number_input("Site (OMNIBEES) — taxa fixa por reserva (R$)", min_value=0.0, value=15.40, step=0.1)

# Cartão
st.sidebar.subheader("Cartão — mediana/padrão para reservas sem taxa informada")
pct_cartao_padrao = st.sidebar.number_input("Taxa de cartão padrão (%)", min_value=0.0, max_value=100.0, value=4.5, step=0.1)

# Taxa administrativa e IRRF
st.sidebar.subheader("Administração e IRRF")
pct_taxa_adm = st.sidebar.number_input("Taxa Administrativa do Hotel (%) — sobre o líquido antes do IRRF", min_value=0.0, max_value=100.0, value=10.0, step=0.1)
pct_irrf = st.sidebar.number_input("IRRF do Cotista (%) — sobre o líquido após taxa adm.", min_value=0.0, max_value=100.0, value=0.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.write("**Modelo de dados** esperado em `sample_data/template_rentabilizacao.csv`.")

# ---------------------------
# Upload
# ---------------------------
uploaded = st.file_uploader("Envie sua planilha (CSV ou XLSX)", type=["csv", "xlsx"])

def load_dataframe(file) -> pd.DataFrame:
    if file is None:
        return pd.DataFrame()
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    return df

df = load_dataframe(uploaded)

# ---------------------------
# Regras e Cálculo
# ---------------------------
def comissao_por_canal(canal: str, valor_bruto: float, taxa_parceiro_percent: float) -> float:
    canal_norm = (canal or "").strip().lower()
    if canal_norm in ["walk-in", "walk in", "walkin", "telefone", "whatsapp", "reserva", "recepcao", "recepção", "telefone/whatsapp"]:
        return 0.0
    if canal_norm == "site":
        return float(valor_omnibees)  # taxa fixa
    if not np.isnan(taxa_parceiro_percent):
        return valor_bruto * float(taxa_parceiro_percent) / 100.0
    # padrões
    if canal_norm == "booking":
        return valor_bruto * pct_booking / 100.0
    if canal_norm == "decolar":
        return valor_bruto * pct_decolar / 100.0
    if canal_norm in ["operadora", "operadoras"]:
        return valor_bruto * pct_operadora / 100.0
    # fallback
    return 0.0

def taxa_cartao(forma_pagamento: str, valor_bruto: float, taxa_cartao_percent: float, mediana_cartao: float) -> float:
    if (forma_pagamento or "").strip().lower() != "cartao":
        return 0.0
    if not np.isnan(taxa_cartao_percent):
        return valor_bruto * float(taxa_cartao_percent) / 100.0
    return valor_bruto * mediana_cartao / 100.0

def custo_cafe(manera: str, dias: float, adt: float, ch712: float, ch06: float) -> float:
    metodo = (manera or "").strip().upper()
    if metodo != "POOL":
        return 0.0
    # 1 criança 0-6 free por reserva
    ch06_pagantes = max(0, int(ch06) - int(free_0_6))
    total_dia = adt * preco_cafe_adulto + ch712 * preco_cafe_crianca_7_12 + ch06_pagantes * preco_cafe_crianca_0_6
    return float(dias) * total_dia

def calcular(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df = df_raw.copy()

    # Tipos
    numeric_cols = [
        "dias","valor_bruto","qtd_adultos","qtd_criancas_7_12","qtd_criancas_0_6",
        "taxa_parceiro_percent","taxa_cartao_percent","desconto_campanha","estorno_devolucao"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = np.nan

    # Mediana de taxa de cartão informada no dataset (somente reservas cartão)
    mediana_cartao = (
        df.query("forma_pagamento.str.lower() == 'cartao'", engine="python")["taxa_cartao_percent"]
        .dropna()
        .median()
    )
    if np.isnan(mediana_cartao):
        mediana_cartao = pct_cartao_padrao

    # Cálculos linha a linha
    impostos = df["valor_bruto"] * (aliquota_impostos/100.0)
    comissoes = [
        comissao_por_canal(c, vb, tpp)
        for c, vb, tpp in zip(df["canal_venda"], df["valor_bruto"], df["taxa_parceiro_percent"])
    ]
    comissoes = pd.Series(comissoes, index=df.index)

    taxa_cart = [
        taxa_cartao(fp, vb, tcp, mediana_cartao)
        for fp, vb, tcp in zip(df["forma_pagamento"], df["valor_bruto"], df["taxa_cartao_percent"])
    ]
    taxa_cart = pd.Series(taxa_cart, index=df.index)

    cafes = [
        custo_cafe(mu, dias if not np.isnan(dias) else 0, adt if not np.isnan(adt) else 0,
                   ch712 if not np.isnan(ch712) else 0, ch06 if not np.isnan(ch06) else 0)
        for mu, dias, adt, ch712, ch06 in zip(df["metodo_utilizacao"], df["dias"], df["qtd_adultos"], df["qtd_criancas_7_12"], df["qtd_criancas_0_6"])
    ]
    cafes = pd.Series(cafes, index=df.index)

    desc_campanha = df["desconto_campanha"].fillna(0.0)
    estorno = df["estorno_devolucao"].fillna(0.0)

    liquido_pre_adm = df["valor_bruto"] - (impostos + comissoes + taxa_cart + cafes + desc_campanha + estorno)
    taxa_adm = liquido_pre_adm * (pct_taxa_adm/100.0)
    base_irrf = liquido_pre_adm - taxa_adm
    irrf = base_irrf * (pct_irrf/100.0)
    liquido_repasse = base_irrf - irrf

    out = df.copy()
    out["impostos"] = impostos.round(2)
    out["comissoes"] = comissoes.round(2)
    out["taxa_cartao"] = taxa_cart.round(2)
    out["cafe_manha"] = cafes.round(2)
    out["descontos_outros"] = (desc_campanha + estorno).round(2)
    out["liquido_pre_adm"] = liquido_pre_adm.round(2)
    out["taxa_adm"] = taxa_adm.round(2)
    out["irrf"] = irrf.round(2)
    out["liquido_repasse"] = liquido_repasse.round(2)

    # Totais e KPI's
    receita_bruta = out["valor_bruto"].sum()
    descontos_total = (out["impostos"] + out["comissoes"] + out["taxa_cartao"] + out["cafe_manha"] + out["descontos_outros"] + out["taxa_adm"] + out["irrf"]).sum()
    repasse_liquido = out["liquido_repasse"].sum()
    take_rate = (descontos_total / receita_bruta * 100.0) if receita_bruta else 0.0

    kpis = dict(
        receita_bruta=round(receita_bruta, 2),
        descontos_total=round(descontos_total, 2),
        repasse_liquido=round(repasse_liquido, 2),
        take_rate=round(take_rate, 2),
        mediana_taxa_cartao=round(mediana_cartao, 2),
    )

    return out, kpis

# ---------------------------
# UI
# ---------------------------
if df.empty:
    st.info("Envie um arquivo CSV/XLSX seguindo o modelo para ver os resultados. Exemplo disponível em **sample_data/template_rentabilizacao.csv** no pacote.")
else:
    # Filtros simples
    with st.expander("🔎 Filtros (opcional)"):
        categorias = sorted([c for c in df.get("categoria", pd.Series()).dropna().unique()])
        canais = sorted([c for c in df.get("canal_venda", pd.Series()).dropna().unique()])
        cotistas = sorted([c for c in df.get("proprietario_nome", pd.Series()).dropna().unique()])

        sel_cat = st.multiselect("Categoria", categorias, default=categorias)
        sel_canal = st.multiselect("Canal de venda", canais, default=canais)
        sel_cotista = st.multiselect("Cotista", cotistas, default=cotistas)

        mask = pd.Series(True, index=df.index)
        if "categoria" in df.columns and sel_cat:
            mask &= df["categoria"].isin(sel_cat)
        if "canal_venda" in df.columns and sel_canal:
            mask &= df["canal_venda"].isin(sel_canal)
        if "proprietario_nome" in df.columns and sel_cotista:
            mask &= df["proprietario_nome"].isin(sel_cotista)

        df = df[mask].reset_index(drop=True)

    calculado, kpis = calcular(df)

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receita Bruta (R$)", f"{kpis['receita_bruta']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Descontos Totais (R$)", f"{kpis['descontos_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Repasse Líquido (R$)", f"{kpis['repasse_liquido']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col4.metric("Take Rate (%)", f"{kpis['take_rate']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.caption(f"Mediana de taxa de cartão aplicada quando ausente: **{kpis['mediana_taxa_cartao']}%**.")

    # Tabelas
    st.subheader("📊 Detalhamento por Categoria")
    if "categoria" in calculado.columns:
        by_cat = calculado.groupby("categoria")[["valor_bruto","impostos","comissoes","taxa_cartao","cafe_manha","taxa_adm","irrf","liquido_repasse"]].sum().round(2)
        st.dataframe(by_cat)

    st.subheader("📈 Detalhamento por Canal de Venda")
    if "canal_venda" in calculado.columns:
        by_canal = calculado.groupby("canal_venda")[["valor_bruto","impostos","comissoes","taxa_cartao","cafe_manha","taxa_adm","irrf","liquido_repasse"]].sum().round(2)
        st.dataframe(by_canal)

    st.subheader("🧾 Tabela de Auditoria (por Reserva)")
    st.dataframe(calculado)

    # Download do CSV processado
    csv = calculado.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV com cálculos", data=csv, file_name="rentabilizacao_processada.csv", mime="text/csv")

    st.markdown("<p class='fine-print'>*Observação:* Café da manhã é informado por transparência no cálculo (POOL) e segue a política interna.</p>", unsafe_allow_html=True)
