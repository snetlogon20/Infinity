class CustomError(Exception):

    def __init__(self, error_code, error_message):
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message

        self.error_code_map = {
            "000000": "Success",
            "0000001": "Init",

            "000100": "Oracle Error",
            "000101": "ClickHouse Error",
            "000102": "Plot Error",
            "000103": "Error in Linear regression",
            "000104": "Error in RAG service",
            "000105": "Error in Doc2Txt service",
            "000106": "Error in JSON utility",

            "999999": "Unknown Error",
        }

    def get_error_message(self, error_code, customer_message=""):
        error_message = self.error_code_map.get(error_code, "un-mapped code")
        final_error_message = rf"{error_code}, error_message={error_message} - custom_message={customer_message}"
        return final_error_message