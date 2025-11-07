# Desafio Técnico – Tesouro Direto (Data Engineer)

**Autor:** Jhonatha da Silva Marques  
**Data:** Novembro/2025  

---

## Descrição

Este projeto implementa um pipeline completo de **ETL (Extração, Transformação e Carga)** e uma **API REST** para o dataset do **Tesouro Direto**, conforme o case proposto no desafio técnico.

O pipeline realiza:

1. Leitura do arquivo Excel original;
2. Limpeza, transformação e normalização dos dados;
3. Armazenamento dos resultados em um banco **SQLite** e arquivo **Parquet**;
4. Disponibilização dos dados via API desenvolvida com **FastAPI**.

---

## ⚙ Tecnologias Utilizadas

- **Python 3.12**
- **Pandas**
- **FastAPI**
- **SQLite**
- **SQLAlchemy**
- **Uvicorn**
- **JupyterLab**

---

## Estrutura do Projeto
```bash
> /desafio-tecnico/
>  ├── dados/                # Base original e arquivos processados
>  │   ├── Series_Temporais_Tesouro_Direto.xlsx
>  │   ├── data.db
>  │   └── titulos_tesouro.parquet
>  ├── notebooks/
>  │   └── exploracao_inicial.ipynb
>  ├── src/
>  │   ├── api.py           # Endpoints da API
>  │   ├── database.py      # Conexão com o banco
>  │   ├── models.py        # Modelos ORM (SQLAlchemy)
>  │   ├── pipeline.py      # Pipeline ETL (Excel → SQLite/Parquet)
>  │   └── utils.py         # Funções auxiliares
>  ├── requirements.txt
>  └── README.md
```


##  Execução Local

### 1. Criar e ativar o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar as dependências:

```bash
pip install -r requirements.txt
```

### 3. Executar o pipeline ETL:

```bash
python -m src.pipeline
```

### 4. Iniciar a API FastAPI:

```bash
uvicorn src.api:app --reload
```

### 5. Acessar a documentação interativa:

Abra no navegador → http://127.0.0.1:8000/docs

------

## Endpoints Principais

| Método     | Endpoint                               | Descrição                        |
| ---------- | -------------------------------------- | -------------------------------- |
| **POST**   | `/titulo_tesouro`                      | Adiciona um novo título          |
| **DELETE** | `/titulo_tesouro/{id}`                 | Remove um título                 |
| **PUT**    | `/titulo_tesouro/{id}`                 | Atualiza dados de um título      |
| **PATCH**  | `/titulo_tesouro/{id}`                 | Atualiza parcialmente um título  |
| **GET**    | `/titulo_tesouro/{id_titulo}`          | Retorna o histórico de um título |
| **GET**    | `/titulo_tesouro/comparar`             | Compara títulos                  |
| **GET**    | `/titulos_tesouro/venda/{id_titulo}`   | Consulta vendas por período      |
| **GET**    | `/titulos_tesouro/resgate/{id_titulo}` | Consulta resgates por período    |



## Decisões Técnicas

- **SQLite** foi escolhido por ser leve e ideal para APIs locais e protótipos.
- **FastAPI** oferece performance e documentação automática via Swagger.
- Os dados são tratados e organizados em formato **tidy** (colunas: `periodo`, `tipo_titulo`, `acao`, `valor`, `ano`, `mes`).
- A arquitetura foi modularizada para permitir fácil manutenção e expansão.

------

## Resultados Gerados

- Banco SQLite: `dados/data.db`
- Dataset transformado: `dados/titulos_tesouro.parquet`
- API interativa: http://127.0.0.1:8000/docs

------

## 🧾 Observações

- O ambiente virtual (`.venv`) foi propositalmente **ignorado** do GitHub para manter o repositório leve.
- As dependências estão listadas em `requirements.txt`.

------

## 📬 Contato

📧 **Jhonatha Silva Marques**
Engenheiro de Dados & IA | Especialista em BI & Analytics
 🔗 [LinkedIn – linkedin.com/in/jhonathamarques](https://linkedin.com/in/jhonathamarques)
 💻 [GitHub – JhonMrq5178](https://github.com/JhonMrq5178)
 📍 São Paulo – SP · Brasil
