select distinct
    try_cast(SQ_CANDIDATO as bigint) as id_candidato,
    DS_TP_MOTIVO as tipo_motivo,
    DS_MOTIVO as motivo
from {{ source_csv('motivo_cassacao', 'motivo_cassacao_2026_BRASIL.csv') }}
where try_cast(SQ_CANDIDATO as bigint) is not null
