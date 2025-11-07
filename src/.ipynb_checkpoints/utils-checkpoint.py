import pandas as pd
import re

# IDs fixos por categoria
TITULOS_ID_MAP = {
    "LTN": 1,
    "LFT": 2,
    "NTN-B": 3,
    "NTN-B Principal": 4,
    "NTN-C": 5,
    "NTN-F": 6,
}

def _clean_colname(c: str) -> str:
    c = re.sub(r"\s+", " ", c).strip()
    c = c.replace("\xa0", " ")
    return c

def read_and_transform_excel(path: str) -> pd.DataFrame:
    """
    Lê o Excel original do Tesouro Direto e transforma em formato longo (tidy):
    colunas finais: titulo_id, categoria_titulo, periodo, ano, mes, acao, valor_milhoes, valor_reais
    """
    xls = pd.ExcelFile(path)
    df = pd.read_excel(path, sheet_name=xls.sheet_names[0])

    # Limpa nomes de colunas
    df.columns = [_clean_colname(c) for c in df.columns]

    # Renomeia a segunda coluna para 'periodo'
    df = df.rename(columns={df.columns[1]: "periodo"})

    # Mapeia colunas de venda/resgate -> (acao, categoria)
    colmap = {}
    for c in df.columns[2:]:
        c2 = c.replace("\xa0", " ")
        c2 = c2.replace("Nome da série:", "")
        c2 = c2.replace("Nome da série: ", "")
        c2 = c2.replace("Unidade: R$ (milhões)", "")
        c2 = re.sub(r"Data de atualização:.*$", "", c2)
        c2 = re.sub(r"\s+", " ", c2).strip()

        if "Vendas - Tesouro Direto -" in c2:
            acao = "venda"
            categoria = c2.split("Vendas - Tesouro Direto -", 1)[1].strip()
        elif "Resgates - Tesouro Direto -" in c2:
            acao = "resgate"
            categoria = c2.split("Resgates - Tesouro Direto -", 1)[1].strip()
        else:
            acao = "venda" if "Vendas" in c2 else ("resgate" if "Resgates" in c2 else "venda")
            categoria = c2.split("-")[-1].strip()

        colmap[c] = (acao, categoria)

    # Período = 1º dia do mês
    df["periodo"] = pd.to_datetime(df["periodo"]).dt.to_period("M").dt.to_timestamp()

    # Wide -> Long
    long_df = df.melt(
        id_vars=["periodo"],
        value_vars=list(colmap.keys()),
        var_name="serie",
        value_name="valor_milhoes",
    )

    long_df["acao"] = long_df["serie"].map(lambda s: colmap[s][0])
    long_df["categoria_titulo"] = long_df["serie"].map(lambda s: colmap[s][1])

    # Mantém apenas categorias conhecidas
    long_df = long_df[long_df["categoria_titulo"].isin(TITULOS_ID_MAP.keys())].copy()

    # Tipos e derivadas
    long_df["valor_milhoes"] = pd.to_numeric(long_df["valor_milhoes"], errors="coerce").fillna(0.0)
    long_df["valor_reais"] = long_df["valor_milhoes"] * 1_000_000
    long_df["ano"] = long_df["periodo"].dt.year
    long_df["mes"] = long_df["periodo"].dt.month
    long_df["titulo_id"] = long_df["categoria_titulo"].map(TITULOS_ID_MAP)

    # Regras de qualidade
    long_df = long_df[(long_df["valor_milhoes"] >= 0) & long_df["titulo_id"].notnull()]

    cols = ["titulo_id","categoria_titulo","periodo","ano","mes","acao","valor_milhoes","valor_reais"]
    return long_df[cols].reset_index(drop=True)
