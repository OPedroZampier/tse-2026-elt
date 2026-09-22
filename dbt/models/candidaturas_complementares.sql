with raw as (
    select * from {{ source_csv('candidatos_complementar', 'consulta_cand_complementar_2026_BRASIL.csv') }}
), ranked as (
    select
        try_cast(SQ_CANDIDATO as bigint) as id_candidato,
        try_cast(NR_IDADE_DATA_POSSE as integer) as idade_na_posse,
        nullif(DS_SITUACAO_JULGAMENTO, '#NULO') as situacao_julgamento,
        nullif(DS_SITUACAO_CANDIDATO_URNA, '#NULO') as situacao_urna,
        nullif(ST_REELEICAO, '#NULO') as reeleicao,
        nullif(ST_QUILOMBOLA, '#NULO') as quilombola,
        nullif(ST_DECLARAR_BENS, '#NULO') as declarou_bens,
        row_number() over (partition by SQ_CANDIDATO order by DT_GERACAO desc, HH_GERACAO desc) as rn
    from raw
)
select * exclude (rn) from ranked where rn = 1 and id_candidato is not null
