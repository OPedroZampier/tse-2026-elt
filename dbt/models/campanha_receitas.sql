select
    try_cast(SQ_CANDIDATO as bigint) as id_candidato,
    SG_UF as uf,
    SG_PARTIDO as partido,
    DS_ORIGEM_RECEITA as origem,
    DS_FONTE_RECEITA as fonte,
    sum(try_cast(replace(VR_RECEITA, ',', '.') as decimal(20, 2))) as receitas_brl,
    count(*) as lancamentos,
    count(distinct nullif(NR_CPF_CNPJ_DOADOR, '#NULO')) as doadores_unicos
from {{ source_csv('contas_eleitorais', 'receitas_candidatos_2026_BRASIL.csv') }}
where try_cast(SQ_CANDIDATO as bigint) is not null
group by 1, 2, 3, 4, 5
