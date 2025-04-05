from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt

class BaseRAGSQLInquiry:
    def inquiry(self, agent_type, question):
        pass  # 抽象方法需子类实现

    @classmethod
    def draw_plot(cls, PlotX, PlotY, data_frame):
        pass

    @classmethod
    def write_form(cls, data_frame, explanation_in_English, explanation_in_Mandarin, sql):
        pass

    @classmethod
    def write_excel(cls, edited_data_frame):
        pass