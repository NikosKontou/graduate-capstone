import matplotlib.pyplot as plt
import seaborn as sns

def plot_bet_vs_win(df):
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.scatterplot(data=df, x="betbaseamount", y="wonbaseamount", hue="game_provider_id", ax=ax)
    sns.despine()
    return fig