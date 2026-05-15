def get_kpi_metrics(client, table_name: str, min_bet: float, providers: list, game_ids: list, env: str):
    provider_str = ', '.join(map(str, providers))
    where_clause = f"WHERE betbaseamount >= {min_bet} AND game_provider_id IN ({provider_str})"

    if game_ids:
        game_id_str = ', '.join(map(str, game_ids))
        where_clause += f" AND game_id IN ({game_id_str})"

    # Handle SQL dialect differences
    if env == "BigQuery":
        table_ref = f"`{table_name}`"
        dur_sql = "TIMESTAMP_DIFF(MAX(endtime), MIN(starttime), SECOND)"
        avg_round_sql = "AVG(TIMESTAMP_DIFF(endtime, starttime, SECOND))"
    else:
        table_ref = table_name  # DuckDB views don't need backticks
        dur_sql = "date_diff('second', MIN(starttime), MAX(endtime))"
        avg_round_sql = "AVG(date_diff('second', starttime, endtime))"

    query = f"""
        WITH filtered_data AS (
            SELECT * FROM {table_ref} {where_clause}
        ),
        session_data AS (
            SELECT sessionid, COUNT(*) as spins, {dur_sql} as dur
            FROM filtered_data GROUP BY sessionid
        )
        SELECT 
            (SELECT {avg_round_sql} FROM filtered_data) as avg_round,
            AVG(spins) as avg_spins, 
            AVG(dur) as avg_session
        FROM session_data
    """

    # Execute based on the client type
    return client.query(query).to_dataframe() if env == "BigQuery" else client.execute(query).df()


def get_scatter_data(client, table_name: str, min_bet: float, providers: list, game_ids: list, env: str):
    provider_str = ', '.join(map(str, providers))
    where_clause = f"WHERE betbaseamount >= {min_bet} AND game_provider_id IN ({provider_str})"

    if game_ids:
        game_id_str = ', '.join(map(str, game_ids))
        where_clause += f" AND game_id IN ({game_id_str})"

    table_ref = f"`{table_name}`" if env == "BigQuery" else table_name

    query = f"SELECT betbaseamount, wonbaseamount, game_provider_id FROM {table_ref} {where_clause} LIMIT 1000"

    return client.query(query).to_dataframe() if env == "BigQuery" else client.execute(query).df()