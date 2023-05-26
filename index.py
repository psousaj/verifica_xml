import func


def get_retentions_values(servico):
    # for element in servico.iter():
    # print(element.tag, element.text)
    valores = servico.find('Valores')
    valor_do_servico


data = func.load_xml('216.xml')
for element in data.findall('.//InfNfse'):
    servico = element.find('Servico')

    get_retentions_values(servico)
