import os
import requests
import zipfile
import io
import boto3
import dotenv

dotenv.load_dotenv(dotenv.find_dotenv())

s3_client = None

def get_s3_client():
    global s3_client
    if s3_client is None:
        s3_client = boto3.client("s3")
    return s3_client


def baixar_dre_cvm_para_s3(ano: int, bucket_name: str):
    """
    Baixa o arquivo ZIP anual da CVM, extrai a DRE consolidade e faz o upload
    para o S3 em CSV.
    """
    url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip"
    print(f"Baixando dados da CVM para o ano {ano}... (Isso pode demorar um pouco)")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    response = requests.get(url, timeout=120, headers=headers)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        nome_arquivo_dre = f"itr_cia_aberta_DRE_con_{ano}.csv"
        if nome_arquivo_dre in zip_ref.namelist():
            print(f"Arquivo {nome_arquivo_dre} existe")

            with zip_ref.open(nome_arquivo_dre) as arquivo:
                conteudo_csv = arquivo.read()

            caminho_s3 = f"financial-project/raw/cvm/{nome_arquivo_dre}"

            client = get_s3_client()
            client.put_object(
                Bucket=bucket_name,
                Key=caminho_s3,
                Body=conteudo_csv,
                ContentType="text/csv",
            )
            print(f"Sucesso Arquivo salvo no S3: s3://{bucket_name}/{caminho_s3}")
        else:
            raise FileNotFoundError(f"Arquivo {nome_arquivo_dre} não encontrado dentro do ZIP da CVM.")

if __name__ == "__main__":
    BUCKET_NAME = os.environ["BUCKET_NAME"]
    if not BUCKET_NAME:
        raise ValueError("Configure a variável BUCKET_NAME no arquivo .env")

    baixar_dre_cvm_para_s3(2024, BUCKET_NAME)