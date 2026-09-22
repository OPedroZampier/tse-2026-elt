select
    SG_PARTIDO as partido,
    SG_UF as uf,
    DS_TP_ESPERA_PARTIDARIA as esfera,
    DS_TP_ORIGEM_DOACAO as origem,
    DS_TP_FONTE_RECURSO as fonte,
    sum(try_cast(replace(VR_RECEITA, ',', '.') as decimal(20, 2))) as receitas_brl,
    count(*) as lancamentos
from {{ source_csv('contas_partidarias', 'receita_anual_2026_BRASIL.csv') }}
group by 1, 2, 3, 4, 5
