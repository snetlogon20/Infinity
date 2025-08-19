from plantuml import PlantUML

from dataIntegrator import CommonLib, CommonParameters
import streamlit as st
import json

from dataIntegrator.LLMSuport.RAGFactory.RAGMockedMessager import RAGMockedMessager
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_UML_req2uml_service import RAG_UML_req2uml_service
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_UML_txt2uml_service import RAG_UML_txt2uml_service
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_UML_uml2schema_service import RAG_UML_uml2schema_service
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_UML_uml2testdata_service import RAG_UML_uml2testdata_service
from dataIntegrator.LLMSuport.StreamLit.SteamLitManager.SuperInquiry import SuperInquiry
from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.utility.SQLUtility import SQLUtility

logger = CommonLib.logger
commonLib = CommonLib()

class AnyRequirement(SuperInquiry):


    def __init__(self):
        self.writeLogInfo("__init__ started")

    def display_uml(self, uml_code):
        # Display UML
        plantuml_server = "http://www.plantuml.com/plantuml/png/"
        plantuml = PlantUML(plantuml_server)
        image_url = plantuml.get_url(uml_code)
        st.image(image_url)

    def initialize_session_state(self):
        if 'current_step' not in st.session_state:
            st.session_state.current_step = 0
        if 'step1_req' not in st.session_state:
            st.session_state.step1_req = RAGMockedMessager.txt2req_MOCKED_AI_ANSWER
        if 'step2_req' not in st.session_state:
            st.session_state.step2_req = ""
        if 'step2_uml' not in st.session_state:
            st.session_state.step2_uml = ""
        if 'step3_uml' not in st.session_state:
            st.session_state.step3_uml = ""
        if 'step3_json' not in st.session_state:
            st.session_state.step3_json = ""
        if 'step4_uml' not in st.session_state:
            st.session_state.step4_uml = ""
        if 'step4_sql' not in st.session_state:
            st.session_state.step4_sql = ""
        if 'step5_json' not in st.session_state:
            st.session_state.step5_json = ""
        if 'step5_question' not in st.session_state:
            st.session_state.step5_question = ""

    # Page 1: Txt2req
    def page_txt2req(self):
        st.header("Step 1: Txt2req")
        st.write("Enter your requirements below:")

        # Text area for requirements input
        st.session_state.step1_req = st.text_area(
            "Requirements:",
            value=st.session_state.step1_req,
            height=500,
            placeholder="Enter your requirements here..."
        )

        # # markdown area for requirements input
        # st.markdown(st.session_state.step1_req)

    # Page 2: Req2UML
    def page_req2uml(self):
        st.header("Step 2: Req2UML")
        st.write("Edit requirements and UML diagram:")

        # Requirement text area
        st.session_state.step2_req = st.text_area(
            "Requirements:",
            value=st.session_state.step1_req if not st.session_state.step2_req else st.session_state.step2_req,
            height=500,
            key="step2_req_input"
        )

        # UML editor
        st.session_state.step2_uml = st.text_area(
            "PlantUML Code:",
            value=st.session_state.step2_uml,
            height=500,
            placeholder="@startuml\nclass ClassName {\n  +attribute: type\n  +method()\n}\n@enduml",
            key="step2_uml_editor"
        )

        # UML preview (simulated)
        st.subheader("UML Preview")
        uml_code = st.session_state.step2_uml if st.session_state.step2_uml else (
            "@startuml\nclass ClassName {\n  +attribute: type\n  +method()\n}\n@enduml"
        )
        st.code(uml_code, language="plaintext")

        # # Simulate diagram rendering with a placeholder
        # st.info("PlantUML rendering would appear here in a real implementation")
        # st.image(
        #     "https://mermaid.ink/img/pako:eNpVjLEKAjEQRf9lyRZ7F_GBVtpZ2ImF1hZiY-ISmCRLZoZsLFL431Vw1dzmvfdO4VwZ4WCD8mRgR9vS2pL1HcMxZcXzqV5gA3WXq2UqyQz1U5rQHlzT8U4s9VgV5VtYr4KJZz9O80gR4fG9bFc5dT2z7nI5wOeMv8c0yE4y-oTWtIxGgMf8QkHlqgUfC5tCjQ",
        #     caption="Example PlantUML Diagram")

        self.display_uml(uml_code)

        return

    # Page 3: UML2schema
    def page_uml2schema(self):
        st.header("Step 3: UML2schema")
        st.write("Edit UML and view generated JSON schema:")

        # UML editor
        st.session_state.step3_uml = st.text_area(
            "PlantUML Code:",
            value=st.session_state.step2_uml if not st.session_state.step3_uml else st.session_state.step3_uml,
            height=200,
            key="step3_uml_editor"
        )

        # UML preview (simulated)
        st.subheader("UML Preview")
        uml_code = st.session_state.step3_uml if st.session_state.step3_uml else (
            "@startuml\nclass ClassName {\n  +attribute: type\n  +method()\n}\n@enduml"
        )
        # st.code(uml_code, language="plaintext")
        plantuml_server = "http://www.plantuml.com/plantuml/png/"
        plantuml = PlantUML(plantuml_server)
        image_url = plantuml.get_url(uml_code)
        st.image(image_url)

        # JSON preview
        st.subheader("JSON Schema Preview")

        # Generate JSON from UML (simulated)
        if st.session_state.step3_json:
            json_data = st.session_state.step3_json
        else:
            json_data = {
                "classes": [
                    {
                        "name": "ExampleClass",
                        "attributes": [
                            {"name": "id", "type": "int", "primary_key": True},
                            {"name": "name", "type": "string"}
                        ],
                        "methods": [
                            {"name": "calculate", "parameters": [{"name": "value", "type": "int"}]}
                        ]
                    }
                ]
            }

        json_text = json.dumps(json_data, indent=2)
        st.session_state.step3_json = st.text_area(
            "JSON Schema:",
            value=json_text,
            height=200,
            key="step3_json_preview"
        )

        st.json(json_text)

    # Page 4: UML2testdata
    def page_uml2testdata(self):
        st.header("Step 4: UML2testdata")
        st.write("Edit UML and view generated SQL:")

        # UML editor
        st.session_state.step4_uml = st.text_area(
            "PlantUML Code:",
            value=st.session_state.step3_uml if not st.session_state.step4_uml else st.session_state.step4_uml,
            height=200,
            key="step4_uml_editor"
        )

        # UML preview (simulated)
        st.subheader("UML Preview")
        uml_code = st.session_state.step4_uml if st.session_state.step4_uml else (
            "@startuml\nclass ClassName {\n  +attribute: type\n  +method()\n}\n@enduml"
        )
        st.code(uml_code, language="plaintext")

        # SQL preview
        st.subheader("SQL Preview")

        # Generate SQL from UML (simulated)
        if st.session_state.step4_sql:
            sql_text = st.session_state.step4_sql
        else:
            sql_text = """CREATE TABLE ExampleClass (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL
                    );
                
                    INSERT INTO ExampleClass (name) VALUES 
                    ('Item 1'),
                    ('Item 2'),
                    ('Item 3');"""

        st.session_state.step4_sql = st.text_area(
            "SQL:",
            value=sql_text,
            height=200,
            key="step4_sql_preview"
        )

        st.session_state.step4_sql = st.code(SQLUtility().beautify_sql(sql_text))

    # Page 5: Schema@SQL
    def page_schema_sql(self):
        st.header("Step 5: Schema@SQL")
        st.write("Edit JSON schema and ask a question:")

        # JSON editor
        json_text = st.session_state.step3_json if not st.session_state.step5_json else st.session_state.step5_json
        st.session_state.step5_json = st.text_area(
            "JSON Schema:",
            value=json_text,
            height=200,
            key="step5_json_editor"
        )

        # Question input
        st.session_state.step5_question = st.text_area(
            "Ask a question about the schema:",
            value=st.session_state.step5_question,
            height=100,
            placeholder="Enter your question here...",
            key="step5_question_input"
        )

    # Main app logic
    def main(self):
        self.initialize_session_state()

        st.title("Design Wizard")

        # Step navigation/progress indicator
        # 在main函数中替换进度指示器部分
        steps = ["Txt2req", "Req2UML", "UML2schema", "UML2testdata", "Schema@SQL"]
        current_step = st.session_state.current_step

        # 创建进度容器
        progress_container = st.container()
        with progress_container:
            # 使用Streamlit列布局替代原始HTML
            cols = st.columns(len(steps))

            for i, step in enumerate(steps):
                with cols[i]:
                    # 确定圆圈颜色
                    if i < current_step:
                        circle_color = "#4CAF50"  # 已完成 - 绿色
                    elif i == current_step:
                        circle_color = "#1E88E5"  # 当前步骤 - 蓝色
                    else:
                        circle_color = "#E0E0E0"  # 未完成 - 灰色

                    # 创建圆圈
                    circle_html = f"""
                    <div style="
                        height: 30px; 
                        width: 30px; 
                        border-radius: 50%; 
                        background-color: {circle_color};
                        color: white; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        margin: 0 auto;
                        position: relative;
                        z-index: 2;
                    ">{i + 1}</div>
                    """
                    st.markdown(circle_html, unsafe_allow_html=True)

                    # 步骤名称
                    font_weight = "bold" if i == current_step else "normal"
                    st.markdown(
                        f'<div style="text-align: center; font-size: 12px; font-weight: {font_weight}">{step}</div>',
                        unsafe_allow_html=True
                    )

            # 添加连接线
            st.markdown(
                """
                <style>
                .progress-connector {
                    position: absolute;
                    height: 2px;
                    top: 15px;
                    z-index: 1;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # 计算连接线位置和颜色
            connector_html = ""
            for i in range(1, len(steps)):
                left_pos = (i - 1) * (100 / len(steps)) + 50 / len(steps)
                width = 100 / len(steps)

                if i <= current_step:
                    color = "#4CAF50"  # 已完成 - 绿色
                elif i == current_step + 1:
                    color = "#1E88E5"  # 当前步骤连接线 - 蓝色
                else:
                    color = "#E0E0E0"  # 未完成 - 灰色

                connector_html += f"""
                <div class="progress-connector" 
                     style="left: {left_pos}%; 
                            width: {width}%;
                            background-color: {color};">
                </div>
                """

            st.markdown(connector_html, unsafe_allow_html=True)

        # 在进度指示器下方添加间距
        st.markdown('<div style="margin-bottom: 30px;"></div>', unsafe_allow_html=True)

        # Render current step
        if st.session_state.current_step == 0:
            self.page_txt2req()
        elif st.session_state.current_step == 1:
            self.page_req2uml()
        elif st.session_state.current_step == 2:
            self.page_uml2schema()
        elif st.session_state.current_step == 3:
            self.page_uml2testdata()
        elif st.session_state.current_step == 4:
            self.page_schema_sql()

        # Bottom buttons
        col1, col2, col3 = st.columns([1, 1, 1])

        st.markdown("""
        <style>
            div.stButton > button {
                width: 100%;
                transition: all 0.3s ease;
                margin: 5px 0;
            }
            div.stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            div.stButton > button:active {
                transform: translateY(1px);
            }
        </style>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.session_state.current_step > 0:
                if st.button("Previous", use_container_width=True):
                    st.session_state.current_step -= 1
                    st.rerun()

        with col2:
            if st.button("⚡ Generate Code and Next", use_container_width=True, type="secondary"):
                step_name = steps[st.session_state.current_step]
                st.success(f"Code generated for {step_name}!")

                # REQ2UML
                if st.session_state.current_step == 0:
                    question = "请按照要求生成 Database UML和建表语句,并按照JSON格式返回"
                    rag_uml_req2uml_service = RAG_UML_req2uml_service()
                    response_dict = rag_uml_req2uml_service.inquiry(CommonParameters.Default_AI_Engine, question)
                    st.session_state.step2_uml = response_dict["create_table_uml_statement"]
                    st.session_state.current_step += 1
                # UML2SCHEMA
                elif st.session_state.current_step == 1:
                    question = "请按照要求生成 Database UML和建表语句,并按照JSON格式返回"
                    rag_uml_uml2schema_service = RAG_UML_uml2schema_service()
                    response_dict = rag_uml_uml2schema_service.inquiry(CommonParameters.Default_AI_Engine, question)
                    st.session_state.step3_json = response_dict["table_schema"]
                    st.session_state.current_step += 1
                # UML2TESTDATA
                elif st.session_state.current_step == 2:
                    question = "请按照要求生成 Database UML和建表语句,并按照JSON格式返回"
                    rag_uml_uml2testdata_service = RAG_UML_uml2testdata_service()
                    response_dict = rag_uml_uml2testdata_service.inquiry(CommonParameters.Default_AI_Engine, question)

                    sql = ""
                    delete_sql_list = response_dict["delete_sql"]
                    for delete_sql in delete_sql_list:
                        sql = rf"{sql}{delete_sql}"

                    insert_sql_list = response_dict["insert_sql"]
                    for insert_sql in insert_sql_list:
                        sql = rf"{sql}{insert_sql}"

                    update_sql_list = response_dict["update_sql"]
                    for update_sql in update_sql_list:
                        sql = rf"{sql}{update_sql}"

                    st.session_state.step4_sql = sql

                    st.session_state.current_step += 1
                st.rerun()

        with col3:
            if st.session_state.current_step < len(steps) - 1:
                if st.button("Next", use_container_width=True, type="primary"):
                    st.session_state.current_step += 1
                    st.rerun()

        # Add some spacing
        st.write("")
        st.write("")

        # Footer
        st.markdown("---")
        st.caption("Design Wizard - Transform requirements into implementation artifacts")

    @classmethod
    def request_for_rag_inquiry(self, question):
        if question is None or len(question) == 0:
            logger.info("question is null")
            return

        logger.info("request_for_rag_inquiry started")

        try:
            agent_type = CommonParameters.Default_AI_Engine
            service = RAG_UML_txt2uml_service()
            response_dict = service.inquiry(agent_type, question)
            return response_dict
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104", custom_error_message=rf"Error when executing RAG service", e=e)

        logger.info("request_for_rag_inquiry finished")