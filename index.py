import math
import os
import func
from utils import retention_tax
from tools import Logger

logger = Logger(__name__)


class XMLParseCheck:
    """Parses and checks values from XML notes."""

    def __init__(self, nota):
        self.valores = {
            'irpj': 0,
            'csll': 0,
            'pis': 0,
            'cofins': 0,
            'valor_nota': 0,
            'valor_liquido': 0,
        }
        self.retentions = 0
        self.validation_results = {}
        self.nota = self.load_xml(nota)
        self.filename = nota
        self.prestador_cnpj = ""
        self.tomador_cpf_cnpj = ""
        self.file_date = self.get_xml_section(self.nota, 'DataEmissao').text
        self.get_cnpj()
        self.get_retention_values(
            self.get_xml_section(
                self.nota,
                'Servico'
            )
        )

    @staticmethod
    def load_xml(nota):
        return func.load_xml(nota)

    def has_retentions(self):
        return True if self.retentions != 0 else False

    def note_was_cancelled(self):
        try:
            cancelamento = self.get_xml_section(
                self.nota, 'ConfirmacaoCancelamento', area='.//CancelamentoNfse')
            cancelamento = (cancelamento
                            .find('InfConfirmacaoCancelamento')
                            .find('Sucesso')
                            .text
                            )
        except Exception:
            return False

        return True

    @staticmethod
    def extract_and_convert(element, tag, type=float):
        text = func.extract_text(element, tag)
        return type(text) if text else 0.0

    def get_retention_values(self, servico):
        valores = servico.find('Valores')
        self.valores.update({
            'valor_liquido': self.extract_and_convert(valores, 'ValorLiquidoNfse'),
            'valor_nota': self.extract_and_convert(valores, 'ValorServicos'),
            'irpj': self.extract_and_convert(valores, 'ValorIr'),
            'csll': self.extract_and_convert(valores, 'ValorCsll'),
            'pis': self.extract_and_convert(valores, 'ValorPis'),
            'cofins': self.extract_and_convert(valores, 'ValorCofins'),
        })
        self.retentions = sum(value for key, value in self.valores.items(
        ) if key not in ['valor_nota', 'valor_liquido'])

    def get_xml_section(self, data, section, area='.//InfNfse'):
        for element in data.findall(area):
            return element.find(section)

        # get_retention_values(servico)

    def __calculate_value(self, key: str):
        return float(self.valores['valor_nota'] * retention_tax[key.upper()].value) if not 0 else 0

    def validate_values(self, show_values=False):
        validation_results = {}
        values = self.valores.copy()
        values.pop('valor_nota', None)
        values.pop('valor_liquido', None)

        for key in values:
            expected_value = self.__calculate_value(key)
            validation_results[key] = (expected_value, math.isclose(
                values[key], expected_value, abs_tol=0.05))

        if all(result[1] for result in validation_results.values()):
            soma_liquido = float("{:.2f}".format(
                self.valores['valor_nota'] - self.retentions))
            validation_results['valor_liquido'] = soma_liquido, math.isclose(
                soma_liquido, self.valores['valor_liquido'], abs_tol=0.05)

        else:
            false_values = [
                k for k, v in validation_results.items() if not v[1]]
            raise ValueError(
                f'As retenções a seguir estão erradas: {false_values} - CNPJ: Prestador:{self.prestador_cnpj}, Tomador:{self.tomador_cpf_cnpj}\n{self.filename}')

        if show_values:
            self.validation_results = validation_results
            return self.validation_results
        else:
            self.validation_results = {k: v[1]
                                       for k, v in validation_results.items()}
            return self.validation_results

    def get_cnpj(self):
        prestador = self.get_xml_section(
            self.nota,
            'PrestadorServico'
        ).find('IdentificacaoPrestador')
        tomador = (self.get_xml_section(
            self.nota,
            'TomadorServico')
            .find('IdentificacaoTomador')
            .find('CpfCnpj'))

        self.prestador_cnpj = func.extract_text(prestador, 'Cnpj')
        self.tomador_cpf_cnpj = func.extract_text(
            tomador, 'Cnpj', opcional='Cpf')


def __init__(xml):
    print('--'*50, '\n')
    parser = XMLParseCheck(xml)

    def display_results(parser: XMLParseCheck, retentions=False):
        print(
            f"\nArquivo: {parser.filename} / Prestador: {parser.prestador_cnpj} / Tomador: {parser.tomador_cpf_cnpj}\n{parser.file_date}\n")
        print(parser.valores)
        if retentions:
            print(parser.validation_results)
            print("Retentions: ", parser.retentions)

    try:
        if parser.note_was_cancelled():
            raise ValueError(f'Esta nota foi cancelada: {parser.filename}')

        if len(parser.tomador_cpf_cnpj) == 11 and parser.has_retentions():
            raise ValueError(
                f'NFS-e não deve haver retenção para CPF: {parser.filename}')

        if func.validate_simples(parser.tomador_cpf_cnpj, parser.prestador_cnpj) and parser.has_retentions():
            parser.validate_values()
            display_results(parser, retentions=True)
        else:
            if parser.has_retentions():
                raise ValueError(
                    f'Não deve haver retenção entre Optantes do Simples: {parser.filename}')

            display_results(parser)

    except KeyError as e:
        logger.info(f"{xml}-{e}")

    except ValueError as e:
        raise ValueError(e)


if __name__ == '__main__':
    directory = 'xml'
    erros_count = 0
    erros = []
    for xml in os.listdir(directory):
        try:
            if os.path.isfile(os.path.join(directory, xml)):
                file = os.path.join(directory, xml)
                __init__(file)
        except ValueError as e:
            erros_count += 1
            erros.append(f"ERRO: {e}")
        except Exception as e:
            logger.info(e)
            # pass

    print("\n", "//"*25, "\n")
    print("Erros:", erros_count)
    [print(erro) for erro in erros]
