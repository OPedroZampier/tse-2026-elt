select
    SG_PARTIDO as partido,
    SG_UF as uf,
    DS_TP_ESFERA_PARTIDARIA as esfera,
    TP_DESPESA as tipo_despesa,
    sum(try_cast(replace(VR_GASTO, ',', '.') as decimal(20, 2))) as gastos_brl,
    sum(try_cast(replace(VR_PAGAMENTO, ',', '.') as decimal(20, 2))) as pagamentos_brl,
    count(*) as lancamentos
from {{ source_csv('contas_partidarias', 'despesa_anual_2026_BRASIL.csv') }}
group by 1, 2, 3, 4
