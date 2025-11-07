from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import get_db, Base, engine
from .models import Titulo, Movimento
from .utils import TITULOS_ID_MAP

app = FastAPI(title="Tesouro Direto API", version="1.0.0")

# garante que as tabelas existem
Base.metadata.create_all(bind=engine)

class MovimentoCreate(BaseModel):
    categoria_titulo: str = Field(..., examples=["NTN-B"])
    mes: int
    ano: int
    acao: str = Field(..., pattern="^(venda|resgate)$")
    valor: float = Field(..., ge=0)

class MovimentoUpdate(BaseModel):
    mes: Optional[int] = None
    ano: Optional[int] = None
    acao: Optional[str] = Field(None, pattern="^(venda|resgate)$")
    valor: float = Field(..., ge=0)

def _first_day(ano:int, mes:int) -> date:
    return date(ano, mes, 1)

def _titulo_id_by_categoria(categoria: str) -> int:
    if categoria not in TITULOS_ID_MAP:
        raise HTTPException(status_code=400, detail=f"categoria_titulo inválida: {categoria}")
    return TITULOS_ID_MAP[categoria]

# 1) POST - adicionar (soma ao existente)
@app.post("/titulo_tesouro")
def add_valor(mov: MovimentoCreate, db: Session = Depends(get_db)):
    if mov.mes < 1 or mov.mes > 12:
        raise HTTPException(400, "mes deve ser 1..12")
    periodo = _first_day(mov.ano, mov.mes)
    titulo_id = _titulo_id_by_categoria(mov.categoria_titulo)

    existing = db.query(Movimento).filter(
        Movimento.titulo_id==titulo_id,
        Movimento.periodo==periodo,
        Movimento.acao==mov.acao
    ).first()

    if existing:
        existing.valor_reais += float(mov.valor)
        existing.valor_milhoes = existing.valor_reais / 1_000_000.0
        db.commit()
        db.refresh(existing)
        return {"status":"ok","message":"valor somado ao movimento existente","item_id":existing.id}
    else:
        novo = Movimento(
            titulo_id=titulo_id,
            periodo=periodo,
            ano=mov.ano,
            mes=mov.mes,
            acao=mov.acao,
            valor_reais=float(mov.valor),
            valor_milhoes=float(mov.valor)/1_000_000.0
        )
        db.add(novo)
        db.commit()
        db.refresh(novo)
        return {"status":"ok","message":"movimento criado","item_id":novo.id}

# 2) DELETE - remover um movimento
@app.delete("/titulo_tesouro/{id}")
def delete_valor(id: int, db: Session = Depends(get_db)):
    obj = db.get(Movimento, id)
    if not obj:
        raise HTTPException(404, "movimento não encontrado")
    db.delete(obj)
    db.commit()
    return {"status":"ok","deleted_id":id}

# 3) PUT/PATCH - atualizar (substitui)
@app.put("/titulo_tesouro/{id}")
@app.patch("/titulo_tesouro/{id}")
def update_valor(id: int, mov: MovimentoUpdate, db: Session = Depends(get_db)):
    obj = db.get(Movimento, id)
    if not obj:
        raise HTTPException(404, "movimento não encontrado")

    if mov.valor is not None:
        obj.valor_reais = float(mov.valor)
        obj.valor_milhoes = obj.valor_reais / 1_000_000.0
    if mov.acao is not None:
        if mov.acao not in ("venda","resgate"):
            raise HTTPException(400, "acao inválida")
        obj.acao = mov.acao
    if mov.ano is not None:
        obj.ano = int(mov.ano)
        obj.periodo = date(obj.ano, obj.mes, 1)
    if mov.mes is not None:
        if mov.mes < 1 or mov.mes > 12:
            raise HTTPException(400, "mes deve ser 1..12")
        obj.mes = int(mov.mes)
        obj.periodo = date(obj.ano, obj.mes, 1)

    # unicidade (titulo,periodo,acao)
    dup = db.query(Movimento).filter(
        Movimento.id != id,
        Movimento.titulo_id == obj.titulo_id,
        Movimento.periodo == obj.periodo,
        Movimento.acao == obj.acao
    ).first()
    if dup:
        raise HTTPException(409, "já existe um movimento para (titulo,periodo,acao)")

    db.commit()
    db.refresh(obj)
    return {"status":"ok","updated_id":id}

# 4) GET - histórico de um título
@app.get("/titulo_tesouro/{id_titulo}")
def historico_titulo(
    id_titulo: int,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    group_by: Optional[str] = Query(None, pattern="^(ano)$"),
    db: Session = Depends(get_db)
):
    titulo = db.get(Titulo, id_titulo)
    if not titulo:
        raise HTTPException(404, "titulo não encontrado")

    q = db.query(Movimento).filter(Movimento.titulo_id==id_titulo)
    if data_inicio: q = q.filter(Movimento.periodo >= data_inicio)
    if data_fim: q = q.filter(Movimento.periodo <= data_fim)

    if group_by == "ano":
        rows = db.query(
            Movimento.ano,
            func.sum(func.case((Movimento.acao=="venda", Movimento.valor_reais), else_=0)).label("valor_venda"),
            func.sum(func.case((Movimento.acao=="resgate", Movimento.valor_reais), else_=0)).label("valor_resgate"),
        ).filter(Movimento.titulo_id==id_titulo).group_by(Movimento.ano).all()
        historico = [{"ano": r.ano, "valor_venda": r.valor_venda or 0.0, "valor_resgate": r.valor_resgate or 0.0} for r in rows]
    else:
        rows = q.order_by(Movimento.periodo.asc()).all()
        from collections import defaultdict
        tmp = defaultdict(lambda: {"valor_venda":0.0, "valor_resgate":0.0, "ano":None, "mes":None})
        for r in rows:
            key = (r.ano, r.mes)
            tmp[key]["ano"] = r.ano
            tmp[key]["mes"] = r.mes
            if r.acao=="venda":
                tmp[key]["valor_venda"] += r.valor_reais
            else:
                tmp[key]["valor_resgate"] += r.valor_reais
        historico = [{"ano":v["ano"], "mes":v["mes"], "valor_venda":v["valor_venda"], "valor_resgate":v["valor_resgate"]} for v in tmp.values()]
        historico = sorted(historico, key=lambda x: (x["ano"], x["mes"]))

    return {"id": titulo.id, "categoria_titulo": titulo.categoria_titulo, "historico": historico}

# 5) GET - comparar títulos (≥2)
@app.get("/titulo_tesouro/comparar")
def comparar_titulos(
    ids: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    group_by: Optional[str] = Query(None, pattern="^(ano)$"),
    db: Session = Depends(get_db)
):
    ids_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not ids_list or len(ids_list) < 2:
        raise HTTPException(400, "forneça ao menos dois ids")

    if group_by == "ano":
        rows = db.query(
            Movimento.ano,
            Movimento.titulo_id,
            func.sum(func.case((Movimento.acao=="venda", Movimento.valor_reais), else_=0)).label("valor_venda"),
            func.sum(func.case((Movimento.acao=="resgate", Movimento.valor_reais), else_=0)).label("valor_resgate"),
        ).filter(Movimento.titulo_id.in_(ids_list))
        if data_inicio: rows = rows.filter(Movimento.periodo >= data_inicio)
        if data_fim: rows = rows.filter(Movimento.periodo <= data_fim)
        rows = rows.group_by(Movimento.ano, Movimento.titulo_id).all()

        by_year = {}
        for ano, titulo_id, vv, vr in rows:
            by_year.setdefault(ano, [])
            categoria = db.get(Titulo, titulo_id).categoria_titulo
            by_year[ano].append({"id": titulo_id, "categoria_titulo": categoria, "valor_venda": vv or 0.0, "valor_resgate": vr or 0.0})
        payload = [{"ano": ano, "valores": arr} for ano, arr in sorted(by_year.items())]
        return payload
    else:
        rows = db.query(Movimento).filter(Movimento.titulo_id.in_(ids_list))
        if data_inicio: rows = rows.filter(Movimento.periodo >= data_inicio)
        if data_fim: rows = rows.filter(Movimento.periodo <= data_fim)
        rows = rows.order_by(Movimento.periodo.asc()).all()

        from collections import defaultdict
        acc = {}
        for r in rows:
            acc.setdefault((r.ano, r.mes), {})
            d = acc[(r.ano, r.mes)].setdefault(r.titulo_id, {"id": r.titulo_id, "categoria_titulo": "", "valor_venda":0.0, "valor_resgate":0.0})
            if r.acao=="venda":
                d["valor_venda"] += r.valor_reais
            else:
                d["valor_resgate"] += r.valor_reais
        payload = []
        for (ano, mes), tit_map in sorted(acc.items()):
            valores = []
            for tid, dd in tit_map.items():
                dd["categoria_titulo"] = db.get(Titulo, tid).categoria_titulo
                valores.append(dd)
            payload.append({"ano": ano, "mes": mes, "valores": valores})
        return payload

# 6) GET - vendas por período
@app.get("/titulos_tesouro/venda/{id_titulo}")
def vendas_por_periodo(id_titulo: int, data_inicio: Optional[date]=None, data_fim: Optional[date]=None, group_by: Optional[str]=Query(None, pattern="^(ano)$"), db: Session=Depends(get_db)):
    if not db.get(Titulo, id_titulo):
        raise HTTPException(404, "titulo não encontrado")
    q = db.query(Movimento).filter(Movimento.titulo_id==id_titulo, Movimento.acao=="venda")
    if data_inicio: q = q.filter(Movimento.periodo >= data_inicio)
    if data_fim: q = q.filter(Movimento.periodo <= data_fim)
    if group_by=="ano":
        rows = db.query(Movimento.ano, func.sum(Movimento.valor_reais)).filter(Movimento.titulo_id==id_titulo, Movimento.acao=="venda")
        if data_inicio: rows = rows.filter(Movimento.periodo >= data_inicio)
        if data_fim: rows = rows.filter(Movimento.periodo <= data_fim)
        rows = rows.group_by(Movimento.ano).all()
        return [{"ano": a, "valor_venda": v or 0.0} for a, v in rows]
    rows = q.order_by(Movimento.periodo.asc()).all()
    return [{"ano": r.ano, "mes": r.mes, "valor_venda": r.valor_reais} for r in rows]

# 7) GET - resgates por período
@app.get("/titulos_tesouro/resgate/{id_titulo}")
def resgates_por_periodo(id_titulo: int, data_inicio: Optional[date]=None, data_fim: Optional[date]=None, group_by: Optional[str]=Query(None, pattern="^(ano)$"), db: Session=Depends(get_db)):
    if not db.get(Titulo, id_titulo):
        raise HTTPException(404, "titulo não encontrado")
    q = db.query(Movimento).filter(Movimento.titulo_id==id_titulo, Movimento.acao=="resgate")
    if data_inicio: q = q.filter(Movimento.periodo >= data_inicio)
    if data_fim: q = q.filter(Movimento.periodo <= data_fim)
    if group_by=="ano":
        rows = db.query(Movimento.ano, func.sum(Movimento.valor_reais)).filter(Movimento.titulo_id==id_titulo, Movimento.acao=="resgate")
        if data_inicio: rows = rows.filter(Movimento.periodo >= data_inicio)
        if data_fim: rows = rows.filter(Movimento.periodo <= data_fim)
        rows = rows.group_by(Movimento.ano).all()
        return [{"ano": a, "valor_resgate": v or 0.0} for a, v in rows]
    rows = q.order_by(Movimento.periodo.asc()).all()
    return [{"ano": r.ano, "mes": r.mes, "valor_resgate": r.valor_reais} for r in rows]
