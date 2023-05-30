import os
from enum import Enum
from tools import Logger
from httpx import Client
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from typing import Optional, Union

load_dotenv()
logger = Logger(__name__)


class HttpMethod(Enum):
    GET = 'get'
    POST = 'post'
    PATCH = 'patch'
    DELETE = 'delete'


def request_simples(url_servico: str, cnpj: str, method: Union[str, HttpMethod], json: bool = False, body: Optional[dict] = None) -> Client:
    """
    Realiza uma solicitação HTTP simples.

    Args:
        url_servico: A URL do serviço para o qual a solicitação será enviada.
        json: Se a resposta da solicitação deve ser tratada como um objeto JSON.
        body: O corpo da solicitação.
        method: O método HTTP a ser usado para a solicitação.

    Returns:
        A resposta da solicitação.

    Raises:
        ValueError: Se o método fornecido é desconhecido.
    """
    if isinstance(method, str):
        try:
            method = HttpMethod[method.upper()]
        except KeyError:
            raise ValueError(f"Método HTTP desconhecido: {method}")

    if body is not None and method not in [HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH]:
        raise ValueError(
            f"O método HTTP {method.value} não suporta corpo de solicitação")

    params = {'cnpj': cnpj, 'token': os.getenv('TOKEN')}

    with Client(base_url=os.getenv('BASE_URL')) as client:
        request_method = getattr(client, method.value)

        if request_method is None:
            raise ValueError(f"Método HTTP desconhecido: {method.value}")

        kwargs = {"json": body} if body is not None else {}
        response = request_method(url_servico, params=params, **kwargs)

        if response.status_code != 200:
            raise ValueError(
                f'{response}Algo de errado não está certo: {response.text}')

        return response.json() if json else response


def load_xml(path: str):
    """lê e retorna um xml pelo path especificado por parâmetro

    Args:
        - path (str): caminho para o xml

    Returns:
        - {xml}: xml
    """
    data = ET.parse(path).getroot()
    return data


def consulta_optante_simples(cnpj):
    """
    Consulta o status de uma empresa na Receita Federal para verificar se ela é optante pelo Simples Nacional.

    Args:
        cnpj: O CNPJ da empresa a ser consultada.

    Returns:
        True se a empresa é optante pelo Simples Nacional, False caso contrário.

    Raises:
        Exception: Se ocorrer um erro ao fazer a requisição para o serviço.
        ValueError: Se a resposta do serviço não contém os dados esperados.

    Note:
        Esta função faz uma requisição HTTP para o serviço da Receita Federal e espera uma resposta em um formato específico.
        A estrutura da resposta esperada é:

        {
            "data": [
                {
                    "simei_situacao": <str>,
                    "simples_nacional_situacao": <str>,
                    ...
                },
                ...
            ]
        }

        Se a resposta não seguir essa estrutura, a função lançará um ValueError.
    """
    print(f'Consultando status simples: {cnpj}')
    servico_url = '/receita-federal/simples'

    try:
        response = request_simples(
            servico_url, cnpj, HttpMethod.POST, json=True)
    except Exception as e:
        logger.error(f"Erro ao consultar o serviço: {str(e)}")
        raise  # re-lança a exceção para ser tratada pelo chamador

    if not response.get('data'):
        logger.error(f"A resposta não contém 'data': {response}")
        raise ValueError("Resposta inesperada do serviço")

    status_simei = response['data'][0].get('simei_situacao')
    status_simples_nacional = response['data'][0].get(
        'simples_nacional_situacao')

    if not status_simples_nacional:
        raise ValueError(
            f"Resposta inesperada do serviço. A resposta não contém 'simples_nacional_situacao': \n{response}")

    # return status_simples_nacional != 'NÃO optante pelo Simples Nacional'
    return False


def extract_text(element: ET, key: str, opcional='') -> str:
    if element.find(key) is None:
        return element.find(opcional).text

    return element.find(key).text


def validate_simples(tomador_cnpj, prestador_cnpj):
    # tomador_is_simples = consulta_optante_simples(tomador_cnpj)
    # prestador_is_simples = consulta_optante_simples(prestador_cnpj)

    if tomador_cnpj is None or prestador_cnpj is None:
        raise KeyError('Forneça o CNPJ para a consulta seu migué')

    # is_checked = not tomador_is_simples and not prestador_is_simples

    # return f"Tomador: {tomador_is_simples}\nPrestador: {prestador_is_simples}" if not is_checked else is_checked
    return True


if __name__ == "__main__":
    print(consulta_optante_simples("33686252000175"))
