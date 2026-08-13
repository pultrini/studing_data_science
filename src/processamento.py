import json
import os

import boto3
import dotenv
import pandas as pd

dotenv.load_dotenv(dotenv.find_dotenv())

def obter_arquivo_recente_s3(bucket_name: str, prefix: str):
    """Busca o JSON mais recente do S3"""
    s3_client = boto3.client("s3")
    caminho_pasta = f'raw/{prefix}'

    response = s3_client.list_objects(Bucket=bucket_name, Prefix=caminho_pasta)
    if 'Contents' not in response:
        raise ValueError(f"Nenhum arquivo encontrado em {caminho_pasta}")

    arquivos = sorted(response["Contents"], key=lambda x: x["LastModified"], reverse=True)
    chave_recente = arquivos[0]["Key"]

    obj = s3_client.get_object(Bucket=bucket_name, Key=chave_recente)
    conteudo = obj['Body'].read().decode('utf-8')

    return json.loads(conteudo)

def limpar_dados(arquivos: dict) -> pd.DataFrame:
    """Faz a limpeza dos dados e retorna um dataframe com os dados"""
    df = pd.DataFrame(arquivos)
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

    df = df.dropna().reset_index(drop=True)
    return df

def process_ipca(df_ipca: pd.DataFrame) -> pd.DataFrame:
    df = df_ipca.copy()
    df["ipca_aceleracao"] = df["valor"].diff()
    df["ipca_acc_3m"] = df["valor"].rolling(window=3).sum()
    df["ipca_acc_12m"] = df["valor"].rolling(window=12).sum()
    df['ano_mes'] = df['data'].dt.to_period('M')

    return df.dropna().reset_index(drop=True)

def process_selic(df_selic: pd.DataFrame) -> pd.DataFrame:
    df = df_selic.copy()
    df.set_index('data', inplace=True)

    df_mensal = df.resample("ME").agg(
        selic_media_mensal=("valor", "mean"),
        selic_maxima_mensal=("valor", "max"),
        selic_volatilidade=("valor", "std"),
    ).reset_index()

    df_mensal['ano_mes'] = df_mensal['data'].dt.to_period('M')

    return df_mensal.dropna().reset_index(drop=True)

def unificar_dados_macro(df_ipca: pd.DataFrame, df_selic: pd.DataFrame) -> pd.DataFrame:
    df_macro = pd.merge(
        df_selic,
        df_ipca,
        on='ano_mes',
        how='inner',
        suffixes=('_ipca', '_selic'),
    )

    df_macro = df_macro.drop(columns=['data_ipca'])
    df_macro = df_macro.rename(columns={'data_selic': 'data_referencia'})
    return df_macro

if __name__ == "__main__":
    BUCKET = os.environ.get("BUCKET_NAME")
    print("buscando dados Dados")
    dados = obter_arquivo_recente_s3(BUCKET, "macroeconomia")
    print("limpando dados...")
    df_ipca = limpar_dados(dados['ipca'])
    df_selic = limpar_dados(dados['selic'])

    print('Transformando para ter mais dados macroeconimicos')
    df_ipca_features = process_ipca(df_ipca)
    df_selic_features = process_selic(df_selic)

    print("\n--- IPCA Processado ---")
    print(df_ipca_features.tail())

    print("\n--- SELIC Processada ---")
    print(df_selic_features.tail())

    print("Cruzando tabelas...")
    df_macro_final = unificar_dados_macro(df_ipca_features, df_selic_features)
    print(df_macro_final.info())
    print(df_macro_final.tail())

    caminho_saida = "dados_processados_macro.parquet"
    df_macro_final.to_parquet(caminho_saida, index=False)
    print(f"\nArquivo processado com sucesso e salvo em {caminho_saida}")
