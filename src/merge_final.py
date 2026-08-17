import pandas as pd

def criar_tabela_modelagem(caminho_cvm: str, caminho_macro: str) -> pd.DataFrame:
    """Cruza dados contábeis com indicadores macroeconomicos"""

    print("Carregando arquivos parquet")
    df_cvm = pd.read_parquet(caminho_cvm)
    df_macro = pd.read_parquet(caminho_macro)

    print("Realizando o Merge por ano mês")
    # O inner é usado para manter os trimestres das empresas
    df_final = pd.merge(
        df_cvm,
        df_macro,
        how="inner",
        on='ano_mes'
    )

    df_final = df_final.dropna().reset_index(drop=True)

    return df_final


if __name__ == "__main__":
    arquivo_cvm = "dados_cvm_processados.parquet"
    arquivo_macro = "dados_processados_macro.parquet"
    arquivo_saida = "dataset_risco_credito_final.parquet"

    df_modelagem = criar_tabela_modelagem(arquivo_cvm, arquivo_macro)

    print("\n--- Estrutura da Tabela Final (Ouro) ---")
    print(f"Total de registros: {len(df_modelagem)}")
    print(df_modelagem.info())

    print("\n--- Amostra Pronta para Machine Learning ---")
    colunas_amostra = ['DENOM_CIA', 'ano_mes', 'target_lucro', 'selic_media_mensal', 'ipca_acc_12m']
    print(df_modelagem[colunas_amostra].head())

    df_modelagem.to_parquet(arquivo_saida, index=False)
    print(f"\nSucesso! O dataset final foi salvo como '{arquivo_saida}'.")
    df_modelagem.head()
