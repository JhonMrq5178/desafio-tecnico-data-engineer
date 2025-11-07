import pandas as pd
import re

TITULOS_ID_MAP = {
    "LTN": 1,
    "LFT": 2,
    "NTN-B": 3,
    "NTN-B Principal": 4,
    "NTN-C": 5,
    "NTN-F": 6,
}

def _clean_colname(c: str) -> str:
    """remove espaços invisíveis e padroniza texto"""
    c = c.replace("\xa0", " ")
    c = re.sub(r"\s+", " ", c)
    return c.strip()

def read_and_transform_excel(path: str) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    df = pd.read_excel(path, sheet_name=xls.sheet_names[0])
    df.columns = [_clean_colname(c) for c in df.columns]
    df = df.rename(columns={df.columns[1]: "periodo"})

    # mapear colunas “venda/resgate” -> (ação, categoria)
    colmap = {}
    for c in df.columns[2:]:
        base = _clean_colname(c)
        base = re.sub(r"Nome da série: ?", "", base)
        base = re.sub(r"Periodicidade:.*$", "", base)
        base = re.sub(r"Unidade:.*$", "", base)
        base = re.sub(r"Data de atualização:.*$", "", base)
        base = base.replace("Fonte: Tesouro Nacional", "").strip()

        if "Vendas - Tesouro Direto -" in base:
            acao = "venda"
            categoria = base.split("Vendas - Tesouro Direto -", 1)[1].strip()
        elif "Resgates - Tesouro Direto -" in base:
            acao = "resgate"
            categoria = base.split("Resgates - Tesouro Direto -", 1)[1].strip()
        else:
            acao = "venda" if "Vendas" in base else ("resgate" if "Resgates" in base else "venda")
            categoria = base.split("-")[-1].strip()

        colmap[c] = (acao, categoria)

    df["periodo"] = pd.to_datetime(df["periodo"]).dt.to_period("M").dt.to_timestamp()

    long_df = df.melt(id_vars=["periodo"], value_vars=list(colmap.keys()),
                      var_name="serie", value_name="valor_milhoes")

    long_df["acao"] = long_df["serie"].map(lambda s: colmap[s][0])
    long_df["categoria_titulo"] = long_df["serie"].map(lambda s: colmap[s][1])

    # normaliza espaços em categoria (ex: “NTN-B Principal ”)
    long_df["categoria_titulo"] = long_df["categoria_titulo"].str.strip()

    # filtra apenas as categorias conhecidas
    long_df = long_df[long_df["categoria_titulo"].isin(TITULOS_ID_MAP.keys())].copy()

    long_df["valor_milhoes"] = pd.to_numeric(long_df["valor_milhoes"], errors="coerce").fillna(0.0)
    long_df["valor_reais"] = long_df["valor_milhoes"] * 1_000_000
    long_df["ano"] = long_df["periodo"].dt.year
    long_df["mes"] = long_df["periodo"].dt.month
    long_df["titulo_id"] = long_df["categoria_titulo"].map(TITULOS_ID_MAP)

    long_df = long_df[(long_df["valor_milhoes"] >= 0) & long_df["titulo_id"].notnull()]

    cols = ["titulo_id","categoria_titulo","periodo","ano","mes","acao","valor_milhoes","valor_reais"]
    return long_df[cols].reset_index(drop=True)
