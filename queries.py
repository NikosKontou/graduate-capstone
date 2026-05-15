def get_kpi_metrics(con, table_name: str, min_bet: float, providers: list, game_ids: list):
    provider_str = ', '.join(map(str, providers))

    # Base filter
    where_clause = f"WHERE betbaseamount >= {min_bet} AND game_provider_id IN ({provider_str})"

    # Dynamically add game_id filter if the user provided any
    if game_ids:
        game_id_str = ', '.join(map(str, game_ids))
        where_clause += f" AND game_id IN ({game_id_str})"

    query = f"""
        WITH filtered_data AS (
            SELECT * FROM {table_name}
            {where_clause}
        ),
        session_data AS (
            SELECT 
                sessionid, 
                COUNT(*) as spins, 
                date_diff('second', MIN(starttime), MAX(endtime)) as dur
            FROM filtered_data 
            GROUP BY sessionid
        )
        SELECT 
            (SELECT AVG(date_diff('second', starttime, endtime)) FROM filtered_data) as avg_round,
            AVG(spins) as avg_spins, 
            AVG(dur) as avg_session
        FROM session_data
    """
    return con.execute(query).df()


def get_scatter_data(con, table_name: str, min_bet: float, providers: list, game_ids: list):
    provider_str = ', '.join(map(str, providers))
    where_clause = f"WHERE betbaseamount >= {min_bet} AND game_provider_id IN ({provider_str})"

    if game_ids:
        game_id_str = ', '.join(map(str, game_ids))
        where_clause += f" AND game_id IN ({game_id_str})"

    query = f"""
        SELECT betbaseamount, wonbaseamount, game_provider_id 
        FROM {table_name} 
        {where_clause}
        LIMIT 1000
    """
    return con.execute(query).df()