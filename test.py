
import os, shutil
from information_extraction.info_retriever_interface import InfoRetrieverInterface

def clear_output_directory(directory):
    if os.path.exists(directory):
        # Delete all files in the directory
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        # If the directory doesn't exist, create it
        os.makedirs(directory)

def select_document(input_directory):
    doc_list = [doc for doc in os.listdir(input_directory) if doc.endswith('.pdf')]
        
    if len(doc_list) == 1:
        test_doc_path = doc_list[0]
    elif len(doc_list) > 1:
        raise Exception(f'More than one input document found: {doc_list}')
    else:
        raise Exception('No test document found on input directory')
    
    return test_doc_path

def test_information_extraction():

    output_path = os.path.join(os.getcwd() + "/information_extraction/document_output/")
    input_path = os.path.join(os.getcwd() + "/information_extraction/document_input/")

    os.environ['FIS_ENDPOINT'] = input_path

    path_to_test = select_document(os.environ['FIS_ENDPOINT'])
    IE = InfoRetrieverInterface()
    documents = IE.extract_info(path_to_test)

    clear_output_directory(output_path)

    for i, document in enumerate(documents):
        content = f"# {document.name}\n\n"
        content += f"## Tipo de Documento\n{document.document_type}\n\n"
        content += f"## Resumo\n{document.summary}\n\n"
        content += f"## Número da página início\n{document.file_page_start}\n\n"
        content += f"## Número da página fim\n{document.file_page_finish}\n\n"
        content += f"## Data de referência\n{document.reference_date}\n\n"
        content += "## Key Information\n\n"

        for key, value in document.key_information.items():
            content += f"### {key}\n"
            content += f"**Descrição**: {value.get('descrição', 'N/A')}\n\n"
            content += "**Conteúdo:**\n"
            if isinstance(value.get('conteúdo'), dict):
                for subkey, subvalue in value['conteúdo'].items():
                    content += f"- **{subkey}**: {subvalue}\n"
            else:
                content += f"{value.get('conteúdo', 'N/A')}\n"
            content += "\n"

        content += f"## Conteúdo total\n{document.return_txt_content()}\n"

        safe_doc_name = "".join(c for c in document.name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        file_name = f"{i}_{safe_doc_name}.md"
        file_path = os.path.join(output_path, file_name)

        try:
            if os.path.exists(file_path):
                file_path = os.path.join(output_path, file_name + "_second")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error writing to {file_path}: {e}")

if __name__ == '__main__':
    test_information_extraction()