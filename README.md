# ADV

Código para o trabalho final de Tópicos em Inteligência Computacional II.

## How to use

Uma simples rotina de testes foi desenvolvida para demonstrar o funcionamento do sistema. Esta rotina de testes tem duas principais dependencias:
- Um único documento com estensão .pdf presente no diretório information_extraction/document_input um documento default simples estará lá por padrão
- OPENAI_API_KEY inserida no campo designado dentro do docker-compose.yml. Esta key é a que permite o uso da Openai API. 
O output será gerado em formato de arquivos .md, um arquivo para cada documento presente no PDF fornecido como input, e estarão disponívels no diretório information_extraction/document_output. 

## observação
- O código fornecido foi retirado de uma aplicação maior onde fazemos caching de requisições e outras otimizações. O código funciona, mas o tempo de resposta vai ser muito superior ao avaliado originalmente.
- Cuidado: sempre que for executado o teste, o diretório output será limpo totalmente. Não esqueça de salvar o que pretender manter.


