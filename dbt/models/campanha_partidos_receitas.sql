select
    SG_PARTIDO as partido,
    SG_UF as uf,
    DS_ESFERA_PARTIDARIA as esfera,
    DS_ORIGEM_RECEITA as origem,
    DS_FONTE_RECEITA as fonte,
    sum(try_cast(replace(VR_RECEITA, ',', '.') as decimal(20, 2))) as receitas_brl,
    count(*) as lancamentos
from {{ source_csv('contas_eleitorais_partidos', 'receitas_orgaos_partidarios_2026_BRASIL.csv') }}
group by 1, 2, 3, 4, 5
