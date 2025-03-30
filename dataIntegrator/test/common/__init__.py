import unittest
from unittest.mock import patch
import pandas as pd
from dataIntegrator.modelService.BasicQuantifyAnalysisService import CommonCKQuery


class TestCommonCKQuery(unittest.TestCase):

    @patch('dataIntegrator.common.CommonCKQuery.CommonCKQuery.clickhouseClient')
    def test_getQueryResult(self, mock_clickhouseClient):
        # Mock data returned by ClickHouse
        mock_data = [
            (20230101, 'Q1', '202301', None),
            (20230102, 'Q1', '202301', None)
        ]

        # Simulate the execute method to return mock data
        mock_clickhouseClient.execute.return_value = mock_data

        # Call the method under test
        result = CommonCKQuery.getQueryResult()

        # Expected DataFrame from mock data
        expected_df = pd.DataFrame(mock_data)

        # Verify that the DataFrame matches expected output
        pd.testing.assert_frame_equal(result, expected_df)


if __name__ == '__main__':
    unittest.main()