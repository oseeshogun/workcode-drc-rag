from langchain_community.document_loaders import PyPDFLoader

file_path = "https://legalrdc.com/wp-content/uploads/2019/12/Code_du_travail_LegalRDC-1.pdf"

loader = PyPDFLoader(file_path)

docs = loader.load()
