import sqlparse

class SQLUtility:
    def beautify_sql(self, sql: str) -> str:
        """Format SQL with standardized indentation and keyword styling"""
        return sqlparse.format(
            sql,
            reindent=True,          # Auto-align indentation
            keyword_case='upper',  # Convert keywords to uppercase
            identifier_case='lower',  # Keep identifiers lowercase
            use_space_around_operators=True,  # Add spaces around =, >, etc.
            indent_width=4,        # 4-space indentation
            comma_first=False      # Standard comma placement
        )


if __name__ == "__main__":
    # Example usage
    ugly_sql = '''
    select name,age from users where age>18 and status='active' 
    order by created_at desc;
    '''

    pretty_sql = SQLUtility().beautify_sql(ugly_sql)
    print(pretty_sql)