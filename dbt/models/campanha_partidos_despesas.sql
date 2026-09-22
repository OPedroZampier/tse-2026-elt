select
    SG_PARTIDO as partido,
    SG_UF as uf,
    DS_ESFERA_PARTIDARIA as esfera,
    DS_ORIGEM_DESPESA as origem,
    sum(try_cast(replace(VR_DESPESA_CONTRATADA, ',', '.') as decimal(20, 2))) as despesas_contratadas_brl,
    count(*) as lancamentos
from {{ source_csv('contas_eleitorais_partidos', 'despesas_contratadas_orgaos_partidarios_2026_BRASIL.csv') }}
group by 1, 2, 3, 4
