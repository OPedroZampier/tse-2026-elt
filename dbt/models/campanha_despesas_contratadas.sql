select
    try_cast(SQ_CANDIDATO as bigint) as id_candidato,
    SG_UF as uf,
    SG_PARTIDO as partido,
    DS_ORIGEM_DESPESA as origem,
    sum(try_cast(replace(VR_DESPESA_CONTRATADA, ',', '.') as decimal(20, 2))) as despesas_contratadas_brl,
    count(*) as lancamentos,
    count(distinct nullif(NR_CPF_CNPJ_FORNECEDOR, '#NULO')) as fornecedores_unicos
from {{ source_csv('contas_eleitorais', 'despesas_contratadas_candidatos_2026_BRASIL.csv') }}
where try_cast(SQ_CANDIDATO as bigint) is not null
group by 1, 2, 3, 4
