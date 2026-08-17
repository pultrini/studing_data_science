import os
import boto3
import pandas as pd
import io
import dotenv

dotenv.load_dotenv(dotenv.find_dotenv())

def carregar_csvs_cvm_s3(bucket_name: str, anos: list) -> pd.DataFrame:
    """Baixa e empilha csv da CVM direto do s3 para pandas"""
    s3_client = boto3.client("s3")
    lista_dfs = []
    for ano in anos:
        chave_arquivo = f"financial-project/raw/cvm/itr_cia_aberta_DRE_con_{ano}.csv"
        print(f"Lendo {chave_arquivo} do S3...")

        try:
            obj = s3_client.get_object(Bucket=bucket_name, Key=chave_arquivo)
            df_ano = pd.read_csv(io.BytesIO(obj['Body'].read()), sep=';', encoding='latin1')
            lista_dfs.append(df_ano)
        except Exception as e:
            print(f"Aviso: Não foi possível carregar o ano {ano}. Erro: {e}")

    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    return df_consolidado


def limpar_e_criar_target_cvm(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Filtra o lucro líquido e cria a variavel alvo"""
    df = df_raw.copy()

    df = df[(df["ORDEM_EXERC"]=="ÚLTIMO") & (df["CD_CONTA"]==3.11)]
    colunas_uteis = ['CNPJ_CIA', 'DENOM_CIA', 'DT_FIM_EXERC', 'VL_CONTA']
    df = df[colunas_uteis]
    df = df.dropna(subset=["VL_CONTA", "DT_FIM_EXERC"])

    df["DT_FIM_EXERC"] = pd.to_datetime(df["DT_FIM_EXERC"])
    df["VL_CONTA"] = pd.to_numeric(df["VL_CONTA"], errors="coerce")

    df = df.dropna().reset_index(drop=True)

    df['target_lucro'] = (df['VL_CONTA']>0).astype(int)
    df['ano_mes'] = df['DT_FIM_EXERC'].dt.to_period('M')

    return df

if __name__ == "__main__":
    BUCKET = os.environ.get("BUCKET_NAME")
    anos_baixados = [2023, 2025]
    print("Iniciando processamento da CVM...")
    df_raw = carregar_csvs_cvm_s3(BUCKET, anos_baixados)
    print(f"Total de linhas brutas: {len(df_raw)}")

    df_clean = limpar_e_criar_target_cvm(df_raw)

    print(f"Total de linhas após limpeza e filtros: {len(df_clean)}")
    print("\n--- Amostra dos Dados Processados ---")
    print(df_clean[['DENOM_CIA', 'DT_FIM_EXERC', 'VL_CONTA', 'target_lucro']].head(10))

    caminho_saida = "dados_cvm_processados.parquet"
    df_clean.to_parquet(caminho_saida, index=False)
    print(f"\nArquivo da CVM processado e salvo como {caminho_saida}")