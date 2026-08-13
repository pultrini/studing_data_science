import json
import os
from datetime import datetime, timedelta

import boto3
import dotenv
import requests

s3_client = None

def get_s3_client():
    global s3_client
    if s3_client is None:
        s3_client = boto3.client('s3')
    return s3_client

def fetch_bcb_serie_periodo(codigo_bcb: int, dias_atras: int) -> list:
    """
    Busca os dados de uma série na API do Banco Central usando um intervalo de datas
    para não esbarrar no limite máximo de 20 itens do endpoint /ultimos.
    """
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=dias_atras)

    # A API do BCB exige estritamente o formato dd/MM/aaaa
    str_final = data_final.strftime("%d/%m/%Y")
    str_inicial = data_inicial.strftime("%d/%m/%Y")

    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bcb}/dados?formato=json&dataInicial={str_inicial}&dataFinal={str_final}"

    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


def save_to_s3(data: dict, bucket_name: str, prefix: str) -> str:
    """
    Salva o dicionário como um arquivo JSON no Amazon S3.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"raw/{prefix}/{prefix}_{timestamp}.json"
    client = get_s3_client()

    client.put_object(
        Bucket=bucket_name,
        Key=file_name,
        Body=json.dumps(data),
        ContentType="application/json"
    )
    return file_name


def lambda_handler(event, context):
    bucket_name = os.environ.get("BUCKET_NAME")
    if not bucket_name:
        raise ValueError("A variável de ambiente BUCKET_NAME não está configurada.")

    try:
        print("Começando a coleta dos dados do BCB...")

        ipca_data = fetch_bcb_serie_periodo(433, 365)
        selic_data = fetch_bcb_serie_periodo(11, 365)

        dados_macro = {
            "ipca": ipca_data,
            "selic": selic_data,
            "coleta_timestamp": datetime.now().isoformat()
        }

        arquivo_salvo = save_to_s3(dados_macro, bucket_name, "macroeconomia")
        print(f"Sucesso! Arquivo salvo em: {arquivo_salvo}")

        return {
            'statusCode': 200,
            'body': json.dumps({'mensagem': f'Arquivo macroecônomico salvo: {arquivo_salvo}'})
        }

    except Exception as e:
        print(f"Erro durante a execução: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'erro': str(e)})
        }

if __name__ == "__main__":
    dotenv.load_dotenv()
    lambda_handler(event={}, context=None)
