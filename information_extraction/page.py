from langchain_core.prompts import ChatPromptTemplate
import io
import base64
from langchain_openai import ChatOpenAI


class Page:
    def __init__(self):
        ## Contents ##
        self.image = None
        self.encoded_image_url = None
        self.text_content = None
        self.key_information = None
        self.model = ChatOpenAI(model="gpt-4o", temperature=0)
        
        ## References ##
        self.page_number = None
        self.from_document = None
        
    def encode_image(self):
        buffered = io.BytesIO()
        self.image.save(buffered, format="JPEG")
        buffered.seek(0)
        base64_image = base64.b64encode(buffered.read()).decode('utf-8')
        self.encoded_image_url = f"data:image/jpeg;base64,{base64_image}"
        
    def set_image(self, image):
        self.image = image
        self.encode_image()
    
    def extract_text_content(self, model, output_parser, n=0):
        
        
        # Initial prompt attempt
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", f"Numero {n}\nDada a imagem que mandei, retorne o conteúdo em texto o mais próximo possível do que está escrito, claro sem transcrever assinaturas. Identifique no texto assinaturas por meio do símbolo [assinatura] e vistos por meio do símbolo [visto]. Se houver na página alguma indicação do nome do documento de onde essa página pertence, destaque esta informação. \nSe na imagem atual você encontrar pistas de que a página atual é continuação de uma página anterior, como numeração de página diferente de 1, ou numeração de clausulas onde a clausula 1 não está presente no documento, sinalize com breve racional sobre. \nSe não puder ajudar com o meu pedido acima, ignore-o e retorne FALSO e o seu motivo para não poder ajudar."),
                ("user", [
                    {
                        "type": "image_url",
                        "image_url": {"url": "{url_image}"},
                    }
                ]),
            ]
        )
        
        base_chain = prompt_template | self.model | output_parser
        url_image = self.encoded_image_url
        input_data = {"url_image": url_image}
        result = base_chain.invoke(input_data)
        
        if "falso" in result.lower().strip():
            print(f"página retornou FALSO {n}, output: {result}")
            if n <= 5:
                self.extract_text_content(self.model, output_parser, n=n+1)
            else:
                print(f"número de tentativas excedida. ")
        else:
            self.text_content = result
