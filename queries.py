def get_kpi_metrics(con, table_name: str):
    query = f"""
        WITH session_data AS (
            SELECT sessionid, COUNT(*) as spins, date_diff('second', MIN(starttime), MAX(endtime)) as dur
            FROM {table_name} GROUP BY sessionid
        )
        SELECT 
            (SELECT AVG(date_diff('second', starttime, endtime)) FROM {table_name}) as avg_round,
            AVG(spins) as avg_spins, 
            AVG(dur) as avg_session
        FROM session_data
    """
    return con.execute(query).df()

def get_scatter_data(con, table_name: str, min_bet: float, providers: list):
    provider_str = ', '.join(map(str, providers))
    query = f"""
        SELECT betbaseamount, wonbaseamount, game_provider_id 
        FROM {table_name} 
        WHERE betbaseamount >= {min_bet} AND game_provider_id IN ({provider_str}) 
        LIMIT 1000
    """
    return con.execute(query).df()