from sqlalchemy import Column, Integer, String, Float, Date, CheckConstraint, UniqueConstraint, ForeignKey, Index
from sqlalchemy.orm import relationship
from .database import Base

class Titulo(Base):
    __tablename__ = "titulos"
    id = Column(Integer, primary_key=True, autoincrement=False)
    categoria_titulo = Column(String, unique=True, nullable=False)
    movimentos = relationship("Movimento", back_populates="titulo")

class Movimento(Base):
    __tablename__ = "titulos_movimentos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo_id = Column(Integer, ForeignKey("titulos.id"), nullable=False)
    periodo = Column(Date, nullable=False)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    acao = Column(String, nullable=False)  # 'venda' ou 'resgate'
    valor_milhoes = Column(Float, nullable=False)
    valor_reais = Column(Float, nullable=False)

    titulo = relationship("Titulo", back_populates="movimentos")

    __table_args__ = (
        CheckConstraint("acao in ('venda','resgate')", name="ck_acao"),
        UniqueConstraint("titulo_id", "periodo", "acao", name="uq_mov_unico"),
        Index("idx_mov_titulo_periodo", "titulo_id", "periodo"),
        Index("idx_mov_acao_periodo", "acao", "periodo"),
    )