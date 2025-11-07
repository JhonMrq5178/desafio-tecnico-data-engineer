import os
import pandas as pd
from .database import engine, Base, SessionLocal
from .models import Titulo, Movimento
from .utils import TITULOS_ID_MAP, read_and_transform_excel

EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados", "Series_Temporais_Tesouro_Direto.xlsx")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados", "data.db")
PARQUET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados", "titulos_tesouro.parquet")

def init_db():
    Base.metadata.create_all(bind=engine)
    # popular tabela de títulos com IDs fixos
    with SessionLocal() as db:
        for nome, id_ in TITULOS_ID_MAP.items():
            if not db.query(Titulo).filter(Titulo.id == id_).first():
                db.add(Titulo(id=id_, categoria_titulo=nome))
        db.commit()

def upsert_movimentos(df: pd.DataFrame):
    with SessionLocal() as db:
        for row in df.itertuples(index=False):
            existing = db.query(Movimento).filter(
                Movimento.titulo_id==row.titulo_id,
                Movimento.periodo==row.periodo,
                Movimento.acao==row.acao
            ).first()
            if existing:
                # substitui pelo valor do ETL (snapshot confiável)
                existing.valor_milhoes = float(row.valor_milhoes)
                existing.valor_reais = float(row.valor_reais)
                existing.ano = int(row.ano)
                existing.mes = int(row.mes)
            else:
                db.add(Movimento(
                    titulo_id=int(row.titulo_id),
                    periodo=row.periodo.date() if hasattr(row.periodo, 'date') else row.periodo,
                    ano=int(row.ano),
                    mes=int(row.mes),
                    acao=row.acao,
                    valor_milhoes=float(row.valor_milhoes),
                    valor_reais=float(row.valor_reais),
                ))
        db.commit()

def main():
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados"), exist_ok=True)
    init_db()
    df = read_and_transform_excel(EXCEL_PATH)
    # Parquet (opcional)
    try:
        df.to_parquet(PARQUET_PATH, index=False)
    except Exception:
        pass
    # Carrega no SQLite
    upsert_movimentos(df)
    print(f"ETL concluído. Registros processados: {len(df)}. DB: {DB_PATH}")

if __name__ == "__main__":
    main()
