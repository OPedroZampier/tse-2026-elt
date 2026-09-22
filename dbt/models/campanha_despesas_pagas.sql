select
    SG_UF as uf,
    DS_ORIGEM_DESPESA as origem,
    DS_FONTE_DESPESA as fonte,
    sum(try_cast(replace(VR_PAGTO_DESPESA, ',', '.') as decimal(20, 2))) as despesas_pagas_brl,
    count(*) as lancamentos
from {{ source_csv('contas_eleitorais', 'despesas_pagas_candidatos_2026_BRASIL.csv') }}
group by 1, 2, 3
