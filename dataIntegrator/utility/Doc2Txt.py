from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

from dataIntegrator import CommonLib
from dataIntegrator.common.CustomError import CustomError

logger = CommonLib.logger
commonLib = CommonLib()

class Doc2Txt:
    def process_documents(self, param_dict: dict) -> List[str]:

        doc_path = param_dict["input_folder"]

        """多格式文档处理流水线（网页5/7）"""
        loaders = {
            '.pdf': PyMuPDFLoader,
            '.docx': Docx2txtLoader
        }
        docs = []
        for filename in os.listdir(doc_path):
            logger.info(rf"processing file: {filename}")

            ext = os.path.splitext(filename)[1].lower()
            if ext in loaders:
                loader = loaders[ext](os.path.join(doc_path, filename))
                docs.extend(loader.load())

        # 带重叠的文本分块
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "；"]
        )
        processed_docs = []
        for doc in splitter.split_documents(docs):
            processed_docs.append(doc.page_content)
        return processed_docs

    def write_txts(self, param_dict: dict):
        output_path = param_dict["output_path"]
        processed_docs = param_dict["processed_docs"]

        with open(output_path, 'w', encoding='utf-8') as f:
            for doc in processed_docs:
                f.write(doc + '\n')  # 每个文档内容占一行
        logger.info(processed_docs)

    def doc2txt(self, param_dict: dict):
        processed_docs = self.process_documents(param_dict)

        param_dict["processed_docs"] = processed_docs
        self.write_txts(param_dict)

if __name__ == "__main__":
    param_dict = {}
    param_dict["input_folder"] = rf"D:\workspace_python\infinity_data\requirements\Letter of Credit"
    param_dict["output_path"] = r"D:\workspace_python\infinity_data\requirements\Letter of Credit\Letter of Credit Requirement.txt"

    try:
        doc2txt = Doc2Txt()
        doc2txt.doc2txt(param_dict)
    except CustomError as e:
        raise e
    except Exception as e:
        raise commonLib.raise_custom_error(error_code="000105",custom_error_message=rf"Error when executing Doc2Txt conversion service", e=e)

